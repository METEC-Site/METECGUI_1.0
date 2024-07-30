import argparse
import copy
import importlib
import importlib.util
import json
import os
import csv
import datetime
import pandas as pd # NOTE: pandas writing and reading excel also needs packages 'xlrs' and 'openpyxl'
import pathlib
import logging
import threading

from Utils import TimeUtils as tu

METEC_ACCEPTEDDATEFORMATS = ["%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"]

def getArgs(argsMetadata):
    description = argsMetadata['description']
    parser = argparse.ArgumentParser(description=description)
    for arg in argsMetadata['args']:
        parser.add_argument(*arg.pop('name_or_flags'), **arg)
    return parser.parse_args()

def loadClass(moduleName, className):
    module = importlib.import_module(moduleName)
    cls = getattr(module, className)
    return cls

def getSize(dir):
    # Returns size of all files in bytes
    size = 0
    if os.path.isdir(dir):
        for base, subdirs, files in os.walk(dir):
            for file in files:
                filePath = os.path.join(base, file)
                if os.path.exists(filePath):
                    size += os.path.getsize(filePath)
    elif os.path.isfile(dir):
        size = os.path.getsize(dir)
    return size

def getNextTag(currentTag=''):
    """
    returns the next iteration of a unique tag intended to append to a directory name to make it unique.

    The tag is intended to be a string from values a-z. The next tag will be the current tag with the rightmost letter
    increasing by 1 (using the ascii encoding). 'a' becomes 'b', 'b' becomes 'c', and so on. If 'z' is the last letter,
    the string will translate 'z' to 'a', and append another 'a' letter to the tag.

    :Example:
    >>> curTag = 'a'
    >>> nextTag = getNextTag(curTag)
    >>> print(nextTag)
    'b'

    >>> newCurTag = 'z'
    >>> nextTag = getNextTag(newCurTag)
    >>> print(nextTag)
    'aa'

    >>> lastExampleTag = 'az'
    >>> lastNextTag = getNextTag(lastExampleTag)
    >>> print(lastNextTag)
    'aaa'


    :param currentTag:
    :type currentTag: str
    :return: the next tag in the iteration.
    :type return: str

    .. todo::
        * come up with scheme so that letters at position other than the last can change. This was the string isn't a
          bunch of 'a's with a variable letter at the end, but rather a string of different and increasing letters.
    """
    if len(currentTag) == 0:
        return 'a'
    lastChar = currentTag[-1]
    lastAscii = ord(lastChar)  # ascii value of last char
    if lastAscii in range(97, 122):  # ascii for a:z
        tag = currentTag[:-1]
        return tag + chr(lastAscii + 1)
    else:
        return currentTag[:-1] + 'aa'

def loadCSV(csvFilepath):
    return pd.read_csv(csvFilepath)

def loadJson(jsonFilepath):
    with open(jsonFilepath) as cfgFile:
        return json.load(cfgFile)

def loadXLSX(xlsxChannel):
    cfgXlsx = pd.read_excel(xlsxChannel)
    return cfgXlsx

EXTENSION_MAP = {
    ".xlsx": loadXLSX,
    ".xls": loadXLSX,
    ".json": loadJson,
    ".csv": loadCSV
}

def loadFile(filepath):
    filepath = pathlib.Path(filepath)
    ext = filepath.suffix
    if ext in EXTENSION_MAP.keys():
        return EXTENSION_MAP[ext](filepath)

class ConfigRecord(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self['RecordDate'] = self.RecordDate = kwargs.get('RecordDate', None)
        self["RecordTime"] = self.RecordTime = kwargs.get('RecordTime', None)
        self["Filename"] = self.Filename = kwargs.get('Filename', None)
        # self["IsValidFile"] = self.IsValidFile = False
        self["IsValidFile"] = False
        self["LoadedRecord"] = self.LoadedRecord = kwargs.get('LoadedRecord', None)
        self["Notes"] = self.Notes = kwargs.get('Notes', None)
        self["StartTimestamp"] = self.StartTimestamp = kwargs.get('StartTimestamp', None)
        self["EndTimestamp"] = self.EndTimestamp = kwargs.get('EndTimestamp', None)

    @property
    def RecordDate(self):
        return self.get("RecordDate", None)

    @RecordDate.setter
    def RecordDate(self, value):
        self['RecordDate'] = value

    @property
    def RecordTime(self):
        return self.get("RecordTime", None)

    @RecordTime.setter
    def RecordTime(self, value):
        self['RecordTime'] = value

    @property
    def Filename(self):
        return self.get("Filename", None)

    @Filename.setter
    def Filename(self, value):
        self['Filename'] = value

    @property
    def IsValidFile(self):
        try:
            return pathlib.Path(self.Filename).exists()
        except:
            return False

    # @IsValidFile.setter
    # def IsValidFile(self, value):
    #     self['IsValidFile'] = value

    @property
    def LoadedRecord(self):
        return self.get("LoadedRecord", None)

    @LoadedRecord.setter
    def LoadedRecord(self, value):
        self['LoadedRecord'] = value

    @property
    def Notes(self):
        return self.get("Notes", None)

    @Notes.setter
    def Notes(self, value):
        self['Notes'] = value

    @property
    def StartTimestamp(self):
        return self.get("StartTimestamp", None)

    @StartTimestamp.setter
    def StartTimestamp(self, value):
        self['StartTimestamp'] = value

    @property
    def EndTimestamp(self):
        return self.get("EndTimestamp", None)

    @EndTimestamp.setter
    def EndTimestamp(self, value):
        self['EndTimestamp'] = value

def loadSummary(summaryFile, asDF=True):
    logging.warning(f'loadSummary method will be depreciated soon. Recommend switching to SummaryManager instead.')
    if summaryFile is None:
        return None
    summaryAsPath = pathlib.Path(summaryFile)
    summaryLines = {}
    with open(summaryFile, "r") as sFile:
        r = csv.DictReader(sFile)
        next(r) # skip labels
        for line in r:
            recordDate = line['RecordDate']
            recordTime = line['RecordTime']
            d = datetime.datetime.strptime(" ".join([recordDate, recordTime]), "%m/%d/%Y %H:%M:%S")
            recordTimestamp = tu.DTtoEpoch(d)
            filename = pathlib.Path(line['Filename'])
            notes = line['Notes']
            fullPath = pathlib.Path(summaryAsPath.parent).joinpath(filename)
            summaryExt = fullPath.suffix
            try:
                record = EXTENSION_MAP[summaryExt](fullPath, asDF=asDF)
            except Exception as e:
                record = EXTENSION_MAP[summaryExt](fullPath)
            summaryLines[recordTimestamp] = {
                "RecordDate": recordDate,
                "RecordTime": recordTime,
                "Filename": filename,
                "Notes": notes,
                "LoadedRecord": record
            }
    return summaryLines

class SummaryManager():
    """ A class to work with METEC summary/manifest files.

    A summary file is a csv (generally) file that contains a table of filenames, and the dates/times at which the file
    is valid. The format is a 4 column table, with contents matching the following table:

    RecordDate  RecordTime  Filename  Notes
    ==========  ==========  ========  =====
    UTC         UTC         filepath
    ==========  ==========  ========  =====

    The file may or may not have a header, which will match the first line in the table. It will always have columns
    matching those in this table.

    RecordDate: Accepted formats: %Y/%m/%d | %m/%d/%Y

    RecordDate: Accepted formats: %H:%M:%S | %H:%M

    Filepath: is a relative path to the location and name of the file. Generally the summary and files are located
    in the same directory.

     Notes: Any notes the user may want to add to this record.

    """

    def __init__(self, summaryFilepath):
        self.lock = threading.RLock()
        self.summaryFilepath = pathlib.Path(summaryFilepath)
        if not self.summaryFilepath.exists():
            raise FileExistsError(f'Could not generate summary file, path does not exist: {str(self.summaryFilepath)}')
        self.lastSummaryUpdate = self.summaryFileLastChangeTime()
        self.summary = self._loadSummary(self.summaryFilepath)
        self.pathMapToLoadedFile = {}
        self._loadPathMap()

    def getSummaryFilename(self):
        return self.summaryFilepath

    def getRecord(self, timestamp=None, copyFile=True, updateBeforeRead=True, **kwargs):
        with self.lock:
            if not self.isSummaryUpdated() and updateBeforeRead:
                logging.info(f'When attempting to read from the summary {self.summaryFilepath.name}, noticed the file had been changed. Updating summary and performing read.')
                self.reloadSummary()
            if timestamp is None:
                timestamp = tu.nowEpoch()
            with self.lock:
                try:
                    timestamp = int(timestamp)
                except:
                    logging.error(f'Cannot read summary record at timestamp {timestamp}, please pass an integer or a float.')
                    return None
                sKeys = sorted(list(self.summary.keys()))
                if len(sKeys) == 0:
                    logging.error(
                        f'Cannot read summary record at timestamp {timestamp}, - Summary file is Empty.')
                    return None
                for ts in sKeys[::-1]:

                    if ts <= timestamp:
                        cfgRec = self.summary[ts]
                        loadedFile = self._loadFilePath(cfgRec['Filename'])
                        if copyFile:
                            loadedFile = copy.deepcopy(loadedFile)
                        if not loadedFile is None:
                            retDict = ConfigRecord()
                            for k in self.summary[ts].keys():
                                retDict[k]= self.summary[ts][k]

                            retDict['LoadedRecord'] = loadedFile
                            return retDict
                return None

    def getAllRecordsBetween(self, startTimestamp, endTimestamp, copyFile=True, updateBeforeRead=True):
        """

        :param startTimestamp:
        :param endTimestamp:
        :param copyFile:
        :return:
        """
        if not self.isSummaryUpdated() and updateBeforeRead:
            logging.info(
                f'When attempting to read from the summary {self.summaryFilepath.name}, noticed the file had been changed. Updating summary and performing read.')
            self.reloadSummary()
        try:
            startTimestamp = int(startTimestamp)
            endTimestamp = int(endTimestamp)
        except:
            logging.error(f'Invalid read on summary {self.summaryFilepath}, please pass timestamps castable to int ')
            return None
        with self.lock:
            validRecordTimestamps = set()
            for tsKey in self.getValidTimestamps():
                singleRecord = self.summary[tsKey]
                recStart = singleRecord['StartTimestamp']
                recEnd = singleRecord['EndTimestamp']
                if startTimestamp <= recStart and recStart <= endTimestamp:
                    validRecordTimestamps.add(tsKey)
                if startTimestamp <= recEnd and recEnd <= endTimestamp:
                    validRecordTimestamps.add(tsKey)
                if recStart <= startTimestamp and endTimestamp <= recEnd:
                    validRecordTimestamps.add(tsKey)
            sortedValidTS = sorted(validRecordTimestamps)
            allRecords = []
            for ts in sortedValidTS:
                allRecords.append(self.getRecord(ts, copyFile))
            return allRecords

    def getValidTimestamps(self):
        with self.lock:
            allTimestamps = list(self.summary.keys())
            for timestamp in self.summary.keys():
                if not self.summary[timestamp].IsValidFile:
                    allTimestamps.remove(timestamp)
            return list(allTimestamps)

    def _loadSummary(self, summaryFilepath):
        with self.lock:
            hasHeader = False
            with open(summaryFilepath, "r") as sFile:
                r = csv.DictReader(sFile)
                for line in r:

                    if ['UTC', 'UTC', 'filepath', '']== list(line.values()): # version 8 type of row is a dict.
                        hasHeader = True
                    break
            with open(summaryFilepath, "r") as sFile:
                summaryLines = {}
                r = csv.DictReader(sFile)
                if hasHeader:
                    next(r) # skip labels
                for line in r:
                    recordDate = line['RecordDate']
                    recordTime = line['RecordTime']
                    lineDatetime = None
                    for singleFormat in METEC_ACCEPTEDDATEFORMATS:
                        try:
                            lineDatetime = datetime.datetime.strptime(" ".join([recordDate, recordTime]), singleFormat)
                            break
                        except:
                            pass
                    if lineDatetime is None:
                        logging.error(f'Error in summary file {summaryFilepath}. Date or time format {recordDate} {recordTime} does not match any accepted formats.')
                        continue

                    recordTimestamp = tu.DTtoEpoch(lineDatetime)
                    filename = pathlib.Path(summaryFilepath.parent, line['Filename'])
                    notes = line['Notes']
                    cfgDict = ConfigRecord()
                    cfgDict.RecordDate = recordDate
                    cfgDict.RecordTime = recordTime
                    cfgDict.Filename = filename
                    cfgDict.Notes = notes
                    cfgDict.StartTimestamp = recordTimestamp
                    cfgDict.EndTimestamp = tu.MAX_EPOCH

                    summaryLines[recordTimestamp] = cfgDict
                self.lastSummaryUpdate = self.summaryFilepath.stat().st_mtime

                timeCorrectedLines = {}
                for k in sorted(summaryLines.keys()):
                    timeCorrectedLines[k] = summaryLines[k]
                if len(timeCorrectedLines) == 0:
                    return timeCorrectedLines

                timeKey = tu.nowEpoch()
                for startTime in list(timeCorrectedLines.keys())[::-1]:
                    timeCorrectedLines[startTime]['EndTimestamp'] = timeKey
                    timeKey = startTime


                return timeCorrectedLines

    def isSummaryUpdated(self):
        with self.lock:
            return self.summaryFileLastChangeTime() == self.lastSummaryUpdate

    def summaryFileLastChangeTime(self):
        return self.summaryFilepath.stat().st_mtime


    def reloadSummary(self):
        with self.lock:
            if not self.isSummaryUpdated():
                self.summary = self._loadSummary(self.summaryFilepath)
                self._loadPathMap()

    def _loadPathMap(self):
        with self.lock:
            for timestamp, summaryLine in self.summary.items():
                filepath = summaryLine['Filename']
                try:
                    tsUpdated = filepath.stat().st_mtime
                except FileNotFoundError as e:
                    logging.info(f'Summary Manager {self.summaryFilepath.name} cannot load file as it does not exist: {filepath}')
                    tsUpdated = None
                if not filepath in self.pathMapToLoadedFile:
                    # if not present in path map, add it.
                    self.pathMapToLoadedFile[filepath] = {"loadedFile": None, 'tsFileUpdated':tsUpdated}
                if not tsUpdated is None and not self.pathMapToLoadedFile[filepath]['tsFileUpdated'] == tsUpdated:
                    # if timestamp of the pre loaded file and the current file's timestamp are different, update/remove the file.
                    self.pathMapToLoadedFile[filepath] = {"loadedFile": None, 'tsFileUpdated': tsUpdated}

    def _loadFilePath(self, filepath: pathlib.Path):
        with self.lock:
            try:
                if not filepath.exists():
                    return None
                fpStats = self.pathMapToLoadedFile[filepath]
                fileLastUpdated = filepath.stat().st_mtime

                if (fpStats['loadedFile'] is None) or not (fpStats['tsFileUpdated'] == fileLastUpdated):
                    file = loadFile(filepath)
                    fpStats['loadedFile'] = file
                    fpStats['tsFileUpdated'] = fileLastUpdated
                    return file
                if not fpStats['loadedFile'] is None:
                    file = fpStats['loadedFile']
                    return file
            except Exception as e:
                logging.error(f'Could not load file {filepath} from summary {self.summaryFilepath.name} due to exception{e}')
                return None

