import pandas as pd
import numpy as np
import logging
import pathlib
from typing import Literal, get_args

from Utils import FileUtils as fUtils
from Utils import TimeUtils as tu


GSH_LITERAL = Literal['GSH-1','GSH-2','GSH-3','GSH-4']

class GCSummary(fUtils.SummaryManager):
    def __init__(self, *args, **kwargs):
        self.gshRecords = {}
        super().__init__(*args, **kwargs)

    def _loadSummary(self, summaryFilepath, raiseError=True):
        with self.lock:
            for gshName in list(get_args(GSH_LITERAL)):
                gshRecord = pd.read_excel(summaryFilepath, gshName, engine='openpyxl')
                self.gshRecords[gshName] = gshRecord

                for singleFormat in fUtils.METEC_ACCEPTEDDATEFORMATS:
                    try:
                        gshRecord['SampleDatetimeUTC'] = pd.to_datetime(gshRecord['SampleDateUTC'] + " "+ gshRecord['SampleTimeUTC'], format=singleFormat, utc=True)
                        break
                    except:
                        pass
                    raise Exception(
                        f'Error in summary file {summaryFilepath} {gshName}. Date or time format does not match any accepted formats.')
                gshRecord['SampleTimestamp'] = (gshRecord['SampleDatetimeUTC'].astype(np.int64) / 10**9).astype(int)
                gshRecord.sort_values(by='SampleTimestamp', inplace=True)

    def isSummaryFileValid(self, filepath=None):
        try:
            if filepath is None:
                filepath = self.summaryFilepath
            filepath = pathlib.Path(filepath)
            if not filepath.exists():
                return False
            gshRecord = pd.read_excel(filepath, engine='openpyxl')
            if not "SampleDatetimeUTC" in gshRecord.columns:
                return False
        except:
            return False
        return True

    def _loadPathMap(self):
        """ Overwriting parent class _loadPathMap as it is unnecessary in this child class.

        :return: Nothing
        """
        pass

    def _loadFilePath(self, filepath):
        """ Overwriting parent class _loadFilePath as it is unnecessary in this child class.

        :return: Nothing
        """
        pass

    def getRecord(self, timestamp=None, copyFile=True, updateBeforeRead=True, gasHouse:GSH_LITERAL=None):
        if not self.isSummaryUpdated() and updateBeforeRead:
            logging.info(
                f'When attempting to read from the summary {self.summaryFilepath.name}, noticed the file had been changed. Updating summary and performing read.')
            self.reloadSummary()
        if timestamp is None:
            timestamp = tu.nowEpoch()
        try:
            timestamp = int(timestamp)
        except:
            logging.error(
                f'Cannot read summary record at timestamp {timestamp}, please pass an integer or a float.')
            return None
        with self.lock:
            recLine = {
                    "RecordDate": None,
                    "RecordTime": None,
                    "Filename": None,
                    "Notes": f"Missing any entries for GC record {gasHouse} in file {self.summaryFilepath}.",
                    "LoadedRecord": {},
                    "StartTimestamp": None,
                    "EndTimestamp": None
                }
            convertedRec = fUtils.ConfigRecord(**recLine)
            for gshName, thisGSHRec in self.gshRecords.items():
                thisLineLoadedRecord = fUtils.ConfigRecord()
                if thisGSHRec.empty:
                    continue
                allRecordsBeforeTimestamp = thisGSHRec.where(thisGSHRec['SampleTimestamp'] <= timestamp).dropna(how='all')
                allRecordsAfterTimestamp = thisGSHRec.where(thisGSHRec['SampleTimestamp'] > timestamp).dropna(how='all')

                # default assumptions for records. Defaults to the first record.
                correspLine = thisGSHRec.iloc[0]
                thisLineLoadedRecord["Notes"] = f"No valid record matching timestamp {timestamp}. Using the first sample row instead."
                thisLineLoadedRecord["EndTimestamp"] = tu.MAX_EPOCH


                if len(allRecordsAfterTimestamp.index) > 0:
                    # there is a next record, use that as the end timestamp.
                    thisLineLoadedRecord["EndTimestamp"] = allRecordsAfterTimestamp.iloc[0]['SampleTimestamp']
                if len(allRecordsBeforeTimestamp.index) > 0:
                    # Latest record is valid, overwrite defaults with this record's values.
                    correspLine = allRecordsBeforeTimestamp.iloc[-1]
                    thisLineLoadedRecord["Notes"] = ""

                thisLineLoadedRecord["LoadedRecord"] = correspLine
                thisLineLoadedRecord["StartTimestamp"] = correspLine['SampleTimestamp']
                thisLineLoadedRecord["RecordDate"] = correspLine['SampleDateUTC']
                thisLineLoadedRecord["RecordTime"] = correspLine['SampleTimeUTC']
                thisLineLoadedRecord["Filename"] = correspLine['SampleFilepath']
                convertedRec['LoadedRecord'][gshName] = thisLineLoadedRecord
            convertedRec['StartTimestamp'] = min(list(rec['StartTimestamp'] for rec in convertedRec['LoadedRecord'].values()))
            convertedRec['EndTimestamp'] = max(list(rec['EndTimestamp'] for rec in convertedRec['LoadedRecord'].values()))
            return convertedRec

    def getAllRecordsBetween(self, startTimestamp, endTimestamp, gasHouse:GSH_LITERAL='GSH-1', copyFile=True, updateBeforeRead=True):
        if not self.isSummaryUpdated() and updateBeforeRead:
            logging.info(
                f'When attempting to read from the summary {self.summaryFilepath.name}, noticed the file had been changed. Updating summary and performing read.')
            self.reloadSummary()
        try:
            startTimestamp = int(startTimestamp)
            endTimestamp = int(endTimestamp)
        except:
            logging.error(f'Invalid read on summary {self.summaryFilepath}, please pass timestamps castable to int.')
            return None
        with self.lock:
            gshRecord = self.gshRecords[gasHouse]
            validRecords = gshRecord.where(startTimestamp <= gshRecord['SampleTimestamp'] & gshRecord['SampleTimestamp'] <= endTimestamp).dropna(how='all')
            allRecords = []
            if validRecords.empty:
                return allRecords
            firstRowInx = validRecords.index[0]
            if startTimestamp != validRecords.iloc[0]['StartTimestamp'] and not firstRowInx == gshRecord.index[0]:
                # This logic checks if there is a valid record before this, and if the requested startTimestamp falls in that record's time.
                validRecords = pd.concat([gshRecord.iloc[firstRowInx], validRecords])
            recEnd = tu.MAX_EPOCH
            for recInx in reversed(validRecords.index):
                validRow = validRecords.iloc[recInx]
                singleRec = {
                    "RecordDate": validRow['SampleDateUTC'],
                    "RecordTime": validRow['SampleTimeUTC'],
                    "Filename": validRow['SampleFilepath'],
                    "Notes": f"",
                    "LoadedRecord": validRow,
                    "StartTimestamp": validRow['SampleTimestamp'],
                    "EndTimestamp": recEnd
                }
                convertedRec = fUtils.ConfigRecord(**singleRec)
                recEnd = convertedRec['SampleTimestamp']
                allRecords.append(convertedRec)
            return reversed(allRecords)