# from Framework.BaseClasses.FrameworkObject import FOMetaclass, FrameworkObject # commented out to transition to Frameworkv2
from datetime import datetime

from Framework.BaseClasses.Registration.FrameworkRegistration import FrameworkObject

from Utils import FileUtils as fUtils
from Utils import TimeUtils as tu
import pathlib
import pandas as pd

SUMMARY_DATE_FMT = '%m/%d/%Y'
MAN_TIME_FMT = '%H:%M:%S'
MAN_TIME_FMT_FRAC = '%H:%M:%S.%f'

class SummaryFile():
    """ A summary file is a record of what files are valid from startTime to endTime

    Assumptions:
        - records are listed in chronological based on their start timestamps
        - no two summary records can have overlapping timestamps.
            * One may have the same end timestamp as another's start timestamp, however.
    """

    def __init__(self, summaryPath, summaryFolder=None):
        self.summaryPath = pathlib.Path(summaryPath)
        self.summaryFolderPath = summaryFolder if summaryFolder else pathlib.Path(self.summaryPath.parent)
        # used for the user to understand what headers are required in the summary.
        self.headers = {"RecordDate":"UTC", "RecordTime":"UTC", "Filename":"filepath", "Notes":""}
        self.loadedRecordMap = {} # Loaded records mapped to the index of the dataframe of the loaded index.
        self.summaryDF = None # placeholder attribute for the self.summary dataframe created in _loadSummary
        self._loadSummary()

    def _loadSummary(self, trimHeaders=True):
        # trim one row of headers if applicable and return the loaded dataframe
        trim = [1] if trimHeaders else []
        try:
            summary = pd.read_csv(self.summaryPath,header=0, skiprows=trim)
        except UnicodeDecodeError as e:
            summary = pd.read_csv(self.summaryPath, header=0, skiprows=trim, encoding='cp1252')

        # remove all entries currently in the record map.
        for i in list(self.loadedRecordMap.keys()):
            self.loadedRecordMap.pop(i)

        # load all record files and add them to the loaded record map.
        for inx in summary.index:
            row = summary.iloc[inx]
            recordFilename = row['Filename']
            fullFilename = pathlib.Path(self.summaryFolderPath.joinpath(recordFilename))
            loadedFile = self._loadSingleRecord(fullFilename)
            self.loadedRecordMap[inx] = loadedFile
        self.summaryDF = summary

    def _loadSingleRecord(self, recordPath):
        return fUtils.EXTENSION_MAP[recordPath.suffix](recordPath)

    def retrieveSummaryRecord(self, ts=None):
        """return the most recent summary before the specified timestamp."""
        if ts is None:
            ts = tu.nowEpoch()
        relevantSummaryRows = self.summaryDF.apply(lambda df: summaryDateTimeToEpoch(df['RecordDate'], df["RecordTime"]) <= ts, axis=1)
        relevantSummaryRows = relevantSummaryRows[relevantSummaryRows != False]
        relevantInx = relevantSummaryRows.index
        record = self.loadedRecordMap[relevantInx[-1]]
        return record

    def getSummaryOverview(self):
        return self.summaryDF.copy()

    def reloadSummary(self):
        self._loadSummary()

#
# class SummaryRecord():
#     def __init__(self, RecordDate, RecordTime, Notes=None, formatter=None, loggerName=None):
#         self.RecordDate = RecordDate
#         self.RecordTime = RecordTime
#         self.EndDate = None
#         self.EndTime = None
#         self.Notes = Notes
#         self.formatter = formatter
#
#     def toDict(self):
#         d = {
#             "RecordDate": self.RecordDate,
#             "RecordTime": self.RecordTime,
#             "EndDate": self.EndDate,
#             "EndTime": self.EndTime,
#             "Formatter": self.formatter.toDict(),
#             "Filename": self.formatter.getPath(),
#             "Notes": self.Notes
#         }
#         return d
#
#     def loadRecord(self):
#         pass
#
#
#
#     def updateEndTimestamp(self, timestamp):
#         endDate, endTime = manEpochToDT(timestamp)
#         self.setEndDate(endDate)
#         self.setEndTime(endTime)
#
#     def setEndDate(self, endDate):
#         self.EndDate = endDate
#
#     def setEndTime(self, endTime):
#         self.EndTime = endTime
#
#     def startTS(self):
#         return manDTtoEpoch(self.RecordDate, self.RecordTime)
#
#     def endTS(self):
#         if (not self.EndDate is None):
#             if self.EndTime:
#                 return manDTtoEpoch(self.EndDate, self.EndTime)
#             else:
#                 return manDTtoEpoch(self.EndDate, '0:00:00')
#         return tu.MAX_EPOCH
#
def summaryDateTimeToEpoch(date, time):
    """returns epoch time of the date/time string in a summary file."""
    if date == 'current' and time == 'current':
        return tu.MAX_EPOCH
    else:
        try:
            dtFormat = " ".join([SUMMARY_DATE_FMT, MAN_TIME_FMT_FRAC])
            manDT = " ".join([date, time])
            dt = datetime.strptime(manDT, dtFormat)
            ts = tu.DTtoEpoch(dt)
            if dt.strftime(dtFormat) == tu.EpochtoDT(tu.MAX_EPOCH).strftime(dtFormat):
                return tu.MAX_EPOCH
            return ts
        except Exception as e:
            dtFormat = " ".join([SUMMARY_DATE_FMT, MAN_TIME_FMT])
            manDT = " ".join([date, time])
            dt = datetime.strptime(manDT, dtFormat)
            ts = tu.DTtoEpoch(dt)
            if dt.strftime(dtFormat) == tu.EpochtoDT(tu.MAX_EPOCH).strftime(dtFormat):
                return tu.MAX_EPOCH
            return ts
#
# def manEpochToDT(ts):
#     dt = EpochtoDT(ts)
#     date = dt.strftime(tu.MAN_DATE_FMT)
#     time = dt.strftime(MAN_TIME_FMT_FRAC)
#     return date,time
