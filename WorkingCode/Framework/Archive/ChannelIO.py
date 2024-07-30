import csv
import logging
import os
import pathlib
import shutil
from datetime import datetime

from Framework.Archive.Formatters import IndexedCSVFormatter, JSONFormatter, NullFormatter, LoggerFormatter, \
    LineJSONFormatter
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Metadata import Metadata
from Utils import ClassUtils as cu
from Utils.TimeUtils import MIN_EPOCH, MAX_EPOCH, EpochtoDT, DTtoEpoch, nowEpoch


class PathExistsError(Exception):
    pass

class ManifestError(Exception):
    pass

class ChannelExistsError(Exception):
    pass

MAN_DATE_FMT = '%m/%d/%Y'
MAN_TIME_FMT = '%H:%M:%S'
MAN_TIME_FMT_FRAC = '%H:%M:%S.%f'

"""
.. _archiver-channel-type:
CHANNEL_TYPES is a map of the channel type to its metadata, used in the Directory Archiver map the correct formatter
and subdirectory location for a specific channel type. """
# todo: add all channel types to this mapping.
CHANNEL_TYPE_MAP = {
    ChannelType.Data:       {'subdir': 'data',      "manifestSubdir": "data",       'formatter': IndexedCSVFormatter,   'ext': '.csv',      'copyover': False},
    ChannelType.Metadata:   {'subdir': 'metadata',  "manifestSubdir": "metadata",   'formatter': JSONFormatter,         'ext': '.json',     'copyover': True},
    ChannelType.Config:     {'subdir': 'config',    "manifestSubdir": "config",     'formatter': NullFormatter,         'ext': '.cfg',      'copyover': True},
    ChannelType.Manifest:   {'subdir': 'manifest',  "manifestSubdir": "manifest",   'formatter': IndexedCSVFormatter,   'ext': '.manifest', 'copyover': False},
    ChannelType.Index:      {'subdir': 'data',      "manifestSubdir": "index",      'formatter': NullFormatter,         'ext': '.idx',      'copyover': False},
    ChannelType.Log:        {'subdir': 'logs',      "manifestSubdir": "logs",       'formatter': LoggerFormatter,       'ext': '.log',      'copyover': False},
    ChannelType.Event:      {'subdir': 'events',    "manifestSubdir": "events",     'formatter': LineJSONFormatter,     'ext': '.json',     'copyover': False},
    ChannelType.Command:    {'subdir': 'commands',  "manifestSubdir": "commands",   'formatter': LineJSONFormatter,     'ext': '.json',     'copyover': False},
    ChannelType.Response:   {'subdir': 'commands',  "manifestSubdir": "responses",  'formatter': LineJSONFormatter,     'ext': '.json',     'copyover': False},
    ChannelType.Base:       {'subdir': '',          "manifestSubdir": "base",       'formatter': NullFormatter,         'ext': '',          'copyover': False},
    ChannelType.DirConfig:  {'subdir': '',          "manifestSubdir": "archiveCfg", 'formatter': JSONFormatter,         'ext': '.json',     'copyover': False},
    ChannelType.Other:      {'subdir': 'other',     "manifestSubdir": "other",      'formatter': NullFormatter,         'ext': '',          'copyover': True},
    ChannelType.ProxyCommand:{'subdir': 'proxy',    "manifestSubdir": "proxy",      'formatter': NullFormatter,         'ext': '',          'copyover': False},
    ChannelType.ProxyResponse:{'subdir': 'proxy',   "manifestSubdir": "proxy",      'formatter': NullFormatter,         'ext': '',          'copyover': False}
}

class Manifest():
    """ A manifest is a record of what files are valid from startTime to endTime

    Assumptions:
        - records are listed in chronological based on their start timestamps
        - no two manifest records can have overlapping timestamps.
            * One may have the same end timestamp as another's start timestamp, however.
    """

    def __init__(self, archiver, channelInfo, manifestPath, loggerName):
        self.logger = logging.getLogger(loggerName)
        self.manifestPath = manifestPath
        self.archiver = archiver
        self.channelInfo = channelInfo
        self._manifest = []
        # used for the user to understand what headers are required in the manifest.
        self.headers = {"RecordDate":"UTC", "RecordTime":"UTC", "Filename":"filepath", "Notes":""}
        self.ogDirPath = None  # path to the original directory which held the file. Used as relative reference with 'Filename' field.

    def dump(self):
        if not self.archiver.isReadonly():
            if not os.path.exists(os.path.dirname(self.manifestPath)):
                os.makedirs(os.path.dirname(self.manifestPath))
            with open(self.manifestPath, 'w', newline='') as mf:
                w = csv.DictWriter(mf, fieldnames=self.headers.keys())
                w.writeheader()
                w.writerow(self.headers)
                for manifestRecord in self._manifest:
                    manDict = manifestRecord.toDict()
                    rowToWrite = {
                        'RecordDate': manDict['RecordDate'],
                        'RecordTime': manDict['RecordTime'],
                        'Filename': manDict['Filename'],
                        'Notes': manDict['Notes']
                    }
                    w.writerow(rowToWrite)

    def toDict(self):
        manRecords = []
        for singleRecord in self._manifest:
            manRecords.append(singleRecord.toDict())
        d = {
            'manifestPath': self.manifestPath,
            '_manifest': manRecords
        }
        return d

    def addManifestRecord(self, manifestRecord):
        """Add a ManifestRecord to the current manifest.
        """
        # get the previous manifest. Used lated to set its timestamp.
        prevManifest = self.getManifestRecord(manifestRecord.startTS())
        if not self._manifest:
            # case 1: manifest is empty.
            self._manifest.append(manifestRecord)
        else:
            if manifestRecord in self._manifest:
                return True
            for singleRecord in self._manifest: # TODO: Pick up here, not implemented is breaking program. Same timestamp is an issue.
                if singleRecord.startTS() == manifestRecord.startTS() and not (singleRecord is manifestRecord):
                    # records have conflicting/the same record timestamps
                    raise NotImplementedError
            self._manifest.append(manifestRecord)
            self._manifest = list(sorted(self._manifest, key=lambda x: x.startTS()))
        # set the end timestamp of the previous record to be the start timestamp of this record.
        if not prevManifest == manifestRecord and not (prevManifest is None):
            prevManifest.updateEndTimestamp(manifestRecord.startTS())
        # If a record exists after this one, set the end timestamp of this record to be the start timestamp of the next.
        manIdx = self._manifest.index(manifestRecord)
        try:
            manifestRecord.updateEndTimestamp(self._manifest[manIdx+1].startTS())
        except IndexError:
            # no manifest record after this one; it is the latest.
            manifestRecord.updateEndTimestamp(MAX_EPOCH)
        self.dump()
        return True

    def getManifestRecords(self, minTS=MIN_EPOCH, maxTS=MAX_EPOCH):
        manifestsInRange = list(filter(lambda x: minTS <= x.startTS() and x.startTS() <= maxTS, self._manifest))
        if not manifestsInRange:
            return [] # return empty list of manifests; record range is out of manifest range.
        ## Fetch the latest record that overlaps minTS if it exists.
        firstRecord = manifestsInRange[0]
        firstRecordIndex = self._manifest.index(firstRecord)
        if firstRecordIndex > 0 and firstRecord.startTS() > minTS :
            # need to get the record previous and insert it into the beginning of the returned records.
            manifestsInRange.insert(0, self._manifest[firstRecordIndex-1])
        return manifestsInRange

    def getManifestRecord(self, ts=None):
        """return the most recent manifest before the specified timestamp."""
        if ts is None:
            ts = nowEpoch()
        manifestsBeforeTS = list(filter(lambda x: x.startTS() <= ts, self._manifest))
        if not manifestsBeforeTS:
            return None
        manifestsBeforeTS = sorted(manifestsBeforeTS, key=lambda x: x.startTS())
        return manifestsBeforeTS[-1]

class ManifestRecord():
    def __init__(self, RecordDate, RecordTime, Notes=None, formatter=None, loggerName=None):
        self.logger=logging.getLogger(loggerName)
        self.RecordDate = RecordDate
        self.RecordTime = RecordTime
        self.EndDate = None
        self.EndTime = None
        self.Notes = Notes
        self.formatter = formatter

    def toDict(self):
        d = {
            "RecordDate": self.RecordDate,
            "RecordTime": self.RecordTime,
            "EndDate": self.EndDate,
            "EndTime": self.EndTime,
            "Formatter": self.formatter.toDict(),
            "Filename": self.formatter.getPath(),
            "Notes": self.Notes
        }
        return d

    def updateEndTimestamp(self, timestamp):
        endDate, endTime = manEpochToDT(timestamp)
        self.setEndDate(endDate)
        self.setEndTime(endTime)

    def setEndDate(self, endDate):
        self.EndDate = endDate

    def setEndTime(self, endTime):
        self.EndTime = endTime

    def startTS(self):
        return manDTtoEpoch(self.RecordDate, self.RecordTime)

    def endTS(self):
        if (not self.EndDate is None):
            if self.EndTime:
                return manDTtoEpoch(self.EndDate, self.EndTime)
            else:
                return manDTtoEpoch(self.EndDate, '0:00:00')
        return MAX_EPOCH


class ChannelIO():
    """ ChannelIO is a class that wraps a specific channel/channelType - It tracks the evolution of this file over time
     via a manifest"""
    def __init__(self, archiver, channelName, loggerName, importConfig=None, overwrite=True):
        self.logger = logging.getLogger(loggerName)
        self.loggerName = loggerName
        self.archiver = archiver
        self.archiveStartTS = self.archiver.getStartTS()
        self.channelName = channelName
        self.typeMap = {}
        if importConfig:
            self.logger.debug(f'Channel IO received external config to import.')
            self.importExternalConfig(importConfig, overwrite)

    def importExternalConfig(self, importConfig, overwrite=True):
        try:
            self.logger.debug(f'ChannelIO named {self.channelName} attempting to import config as v2')
            self._importConfig_v2(importConfig, overwrite)
        except Exception as e:
            try:
                self.logger.debug(f'Unable to import ChannelIO named {self.channelName} using v2. Attempting to import as v1 instead.')
                self._importConfig_v1(importConfig, overwrite)
            except Exception as e:
                self.logger.debug(f'Unable to import config to ChannelIO named {self.channelName} as either v2 or v1.')

    def _importConfig_v2(self, importConfig, overwrite=True):
        """ Import a channel from a version of the archiver that had a manifest, changing the original paths to be relative to this archive. """
        impChannelName = importConfig['channelName']
        impTypeMap = importConfig['typeMap']
        for channelType, channelInfo in impTypeMap.items():
            if channelType in self.typeMap.keys() and not overwrite:
                self.logger.debug(
                    f'ChannelIO named {self.channelName} attempted to import external channeltype {channelType} but it already exists and overwrite is set to False.')
            else:
                if channelType in self.typeMap.keys():
                    self.logger.debug(
                        f'ChannelIO named {self.channelName} already has channeltype {channelType} but will be overwritten.')
                manDef = channelInfo['manifest']
                mPath = manDef['manifestPath']
                mPath = self._replaceBasepath(mPath)
                manifest = Manifest(self.archiver, self, mPath, self.loggerName)
                ogManifestLines = manDef['_manifest']
                for manRecordDef in ogManifestLines:
                    fmtDef = manRecordDef['Formatter']
                    md = fmtDef['metadata']
                    if md:
                        md = Metadata(**md)
                    recPath = fmtDef['path']
                    recPath = self._replaceBasepath(recPath)
                    #todo: rectify this with idxCSV, either get rid of idx or check if there is an idx file.
                    fmtInst = CHANNEL_TYPE_MAP[channelType]['formatter'](self.channelName, channelType, md, self, readOnly=self.archiver.isReadonly(), path=recPath)
                    manRecord = ManifestRecord(RecordDate=manRecordDef['RecordDate'], RecordTime=manRecordDef['RecordTime'],
                                               Notes=manRecordDef.get('Notes',''), formatter=fmtInst, loggerName=self.loggerName)
                    manifest.addManifestRecord(manRecord)
                self.typeMap[channelType] = {'manifest': manifest}

    def _importConfig_v1(self, importConfig, overwrite=True):
        """ Import a channel from a version of the directory archiver that did not have manifests, changing the original paths to be relative to this archive. """
        for channelType, channelInfo in importConfig.items():
            if channelType in self.typeMap.keys() and not overwrite:
                self.logger.debug(
                    f'ChannelIO named {self.channelName} attempted to import external channeltype {channelType} but it already exists and overwrite is set to False.')
            else:
                if channelType in self.typeMap.keys():
                    self.logger.debug(
                        f'ChannelIO named {self.channelName} already has channeltype {channelType} but will be overwritten.')
                cName = channelInfo['channelName']
                begTS = channelInfo['beginTS']
                md = channelInfo['metadata']
                fmtDef = channelInfo['formatter']

                if begTS:
                    d, t = manEpochToDT(begTS)
                else:
                    d, t = manEpochToDT(nowEpoch())

                # rectify path to current archiver, and apply that to a new instance of a formatter.
                if not channelType == ChannelType.Data:
                    recPath = fmtDef['path']
                else:
                    recPath = fmtDef['csvPath']
                recPath = self._replaceBasepath(recPath)
                fmtInst = CHANNEL_TYPE_MAP[channelType]['formatter'](self.channelName, channelType, md, self, readOnly=self.archiver.isReadonly(), path=recPath)

                # add a new manifest to the current manifest, and then
                manifest = Manifest(self.archiver, self, self.newAbsolutePath(ChannelType.Manifest), self.loggerName)
                manifestRecord = ManifestRecord(d, t, formatter=fmtInst, loggerName=self.loggerName)
                manifest.addManifestRecord(manifestRecord)
                self.typeMap[channelType] = {'manifest': manifest}

    def _replaceBasepath(self, pathStr):
        """Replace the base portion of a path with the current base of the archive

        The portion of the path up until the archive's name will be replaced with the current directory that the archive
        is in. If the archive name does not match with the name of the archive supplied in the path, then this will raise an error.

        Example:
            original path: C:\\Users\\User1\\EndOfBasePath1\\DirectoryName\\subpath\\filename.txt
            archive name: DirectoryName
            new directory location: C:\\Users\\User1\\EndOfBasePath2
            return: C:\\Users\\User1\\EndOfBasePath2\\DirectoryName\\subpath\\filename.txt
            """
        p = pathlib.Path(pathStr)
        archiveName = self.archiver.getArchiveName()
        allsplitPaths = list(p.parts)
        for i in range(0, len(allsplitPaths)):
            if i and os.path.join(*allsplitPaths[0:i]) == self.archiver.getBasePath():# this handles the case that the archive is within the same directory and has been renamed.
                allsplitPaths[i] = archiveName
                return os.path.join(*allsplitPaths)
            elif i and allsplitPaths[i] == self.archiver.getArchiveName(): # handles the case that the archiver has the same name but has been moved.
                baseSplit = list(pathlib.Path(self.archiver.getBasePath()).parts)
                return os.path.join(*[*baseSplit, *allsplitPaths[i:]])
        return None

    def toDict(self):
        serTypeMap = {}
        for channelType, channelDict in self.typeMap.items():
            serManifest = channelDict['manifest'].toDict()
            serDict = {'manifest': serManifest}
            serTypeMap[channelType] = serDict
        mapping = {
            'channelName': self.channelName,
            'typeMap': serTypeMap
        }
        return mapping

    def getManifestPath(self, channelType):
        # archiveBase / archive / manifests / [channelTypeDir] / channelName.manifest
        manSubdir = CHANNEL_TYPE_MAP.get(channelType,{}).get('manifestSubdir', None)
        if manSubdir is None:
            manSubdir = 'miscManifests'
        return os.path.join(self.archiver.getArchivePath(), 'manifests', manSubdir, '.'.join([self.channelName, 'manifest']))

    def getFLO(self, channelType):
        path = self.getLatestPath(channelType)
        if path:
            return open(path)
        return None

    def getLatestPath(self, channelType):
        ci = self.getChannelInfo(channelType)
        if ci:
            mr = ci['manifest'].getManifestRecord(nowEpoch())
            return mr.formatter.getPath()
        return None

    def getLocks(self):
        locks = []
        for channelType, channelInfo in self.typeMap.items():
            man = channelInfo['manifest']
            mrs = man.getManifestRecords()
            for singleMR in mrs:
                try:
                    locks.append(singleMR.formatter.lock)
                except:
                    pass
        return locks

    def dump(self):
        if not self.archiver.isReadonly():
            for channelType, channelInfo in self.typeMap.items():
                manifest = channelInfo['manifest']
                manifest.dump()

    def close(self):
        for channelType, channelInfo in self.typeMap.items():
            mrs = channelInfo['manifest'].getManifestRecords()
            for singleMR in mrs:
                singleMR.formatter.close()

    def addROFile(self, name, channelType, metadata=None, path=None):
        now = nowEpoch()
        d, t = manEpochToDT(now)
        fmtDef = CHANNEL_TYPE_MAP[channelType]['formatter']
        fmtInst = fmtDef(name, channelType, metadata, self, readOnly=True, timestamp=now, path=path)
        mr = ManifestRecord(d, t, formatter=fmtInst)
        try:
            self.addChannelType(channelType, metadata, False, now)
        except ChannelExistsError:
            # channel already exists, don't need to create it again.
            pass
        man = self.typeMap[channelType]['manifest']
        man.addManifestRecord(mr)


    def copy(self, channelType, timestamp, fromPath, subPath=None, fileName=None):
        ci = self.getChannelInfo(channelType)
        if ci:
            cTypeDef = CHANNEL_TYPE_MAP[channelType]
            man = ci['manifest']
            mr = man.getManifestRecord(timestamp)
            if mr:
                formatter = mr.formatter
            else:
                formatter = cTypeDef['formatter'](self.channelName, channelType, None, self, readOnly=self.archiver.isReadonly(),path=fromPath)
                d, t = manEpochToDT(timestamp)
                mr = ManifestRecord(d, t, None, formatter)
                man.addManifestRecord(mr)
            # what if it is the same file???
            if not fromPath == formatter.getPath():
                # already in the channelIO object.
                if not os.path.exists(fromPath):
                    # this happens if running the daFromArchive method. Instead, try to get the file from the local archive instead.
                    self.logger.info(f'No file exists to be copied from path {fromPath}. Attempting to generate filepath from subPath {subPath} and fileName {fileName} instead.')
                    localPath = None
                    try:
                        name, ext = os.path.splitext(fileName)
                        joinedFilename = ''.join([name, cTypeDef['ext']])
                        temp = os.path.join(self.archiver.getArchivePath(), cTypeDef['subdir'], subPath, joinedFilename)
                        if os.path.exists(temp):
                           localPath = temp
                        else:
                            temp = os.path.join(self.archiver.getArchivePath(), cTypeDef['subdir'], subPath, fileName)
                            if os.path.exists(temp):
                                localPath = temp
                    except Exception as e:
                        pass
                    if not localPath or not os.path.exists(localPath):
                        raise FileExistsError(f'Could not copy file from path {fromPath}')
                    else:
                        fromPath = localPath
                if self.archiver.isReadonly():
                    formatter.setPath(formatter.importPath(self, channelType, readOnly=self.archiver.isReadonly(), timestamp=timestamp, path=fromPath))
                else:
                    shutil.copy(fromPath, formatter.getPath())




    def getChannelInfo(self, channelType):
        if channelType in self.typeMap.keys():
            return self.typeMap[channelType]
        return None

    def getChannelTypes(self):
        return self.typeMap.keys()

    def addChannelType(self, channelType, metadata=None, createFirstEntry=True, timestamp=None):
        if timestamp is None:
            timestamp = nowEpoch()
        if channelType in self.typeMap.keys():
            raise ChannelExistsError(f'Channel with channelType {channelType} already exists for channel named {self.channelName}')
        man = Manifest(self.archiver, self, self.getManifestPath(channelType), self.loggerName)
        self.typeMap[channelType] = {'manifest':man}
        if createFirstEntry:
            d, t = manEpochToDT(timestamp)
            formatter = CHANNEL_TYPE_MAP[channelType]['formatter'](self.channelName, channelType, metadata, self, readOnly=self.archiver.isReadonly())
            mr = ManifestRecord(d, t, None, formatter)
            man.addManifestRecord(mr)

    def delete(self, channelType, timestamp=None):
        if timestamp is None:
            timestamp = nowEpoch()
        ci = self.getChannelInfo(channelType)
        if ci:
            mr = ci['manifest'].getManifestRecord(timestamp)
            if mr:
                mr.formatter.delete()

    def read(self, channelType, minTS=MIN_EPOCH, maxTS=MAX_EPOCH, asDF=False, asDask=False):
        # todo: append this to a dict? have some way of merging them together?
        ci = self.getChannelInfo(channelType)
        # allReads = {}
        allReads = []
        if ci:
            manifest = ci['manifest']
            records = manifest.getManifestRecords(minTS, maxTS)
            for singleRecord in records:
                try:
                    if channelType == ChannelType.Data:
                        reading = singleRecord.formatter.read(minTS, maxTS, asDF=asDF, asDask=asDask)
                    else:
                        reading = singleRecord.formatter.read(minTS, maxTS)
                    startTS = singleRecord.startTS()
                    endTS = singleRecord.endTS()
                    dictReading ={"startTimestamp": startTS,
                             "endTimestamp": endTS,
                             'metadata': singleRecord.formatter.metadata,
                             'reading': reading}
                    allReads.append(dictReading)
                except Exception as e:
                    self.logger.error(f'Bad read on channel {self.channelName}: {e}')
        else:
            self.logger.info(f'A read of channel type {channelType} was attempted on Channel name {self.channelName} '
                         f'but channel type {channelType} does not exist.')
        return allReads

    def readAll(self, minTS, maxTS):
        channelReads = {}
        for channelType, channelInfo in self.typeMap.items():
            channelReads[channelType] = self.read(channelType, minTS, maxTS)
        return channelReads

    def write(self, record, channelType=None, timestamp=None, metadata=None):
        if cu.isPackage(record):
            self._writePackage(record)
        else:
            self._write(record, channelType, timestamp, metadata)

    def _write(self, record, channelType, timestamp=None, metadata=None):
        if timestamp is None:
            timestamp = nowEpoch()
        ci = self.getChannelInfo(channelType)
        if not ci:
            raise ChannelExistsError(f'No channel found for type {channelType}')
        manifest = ci['manifest']
        manifestRecord = manifest.getManifestRecord(timestamp)
        if manifestRecord:
            if metadata and (not metadata == manifestRecord.formatter.metadata):
                self.updateChannel(timestamp, channelType, newMetadata=metadata)
            manifestRecord.formatter.writeRow(record)
            return True
        else:
            # no record of the appropriate manifest record exists. Either there are none yet, or this record is before the first record.
            self.updateChannel(timestamp, channelType, None, metadata)
            self._write(channelType, timestamp, metadata, record)
            return True

    def _writePackage(self, package):
        self._write(package.payload, package.channelType, package.timestamp, package.metadata)

    def getPath(self, channelType, timestamp=None):
        if timestamp is None:
            timestamp = nowEpoch()
        ci = self.typeMap.get(channelType)
        if ci:
            mr = ci['manifest'].getManifestRecord(timestamp)
            if mr:
                fName = mr.filename # fName is the relative path starting with the subdir of that channelType.
            else:
                fName = self.newRelativePath(channelType, timestamp)
            return os.path.join(self.archiver.getArchivePath(timestamp), fName)
        return None

    def newRelativePath(self, channelType, ts, subpath=None, name=None):
        """ return a relative filepath from the archive base (of the form '/[subdir]/[subpath]/[name]_[ts][.ext])'"""
        chanDef = CHANNEL_TYPE_MAP[channelType]
        if name is None:
            name = self.channelName
        if chanDef['ext']:
            fileName = "".join([name, f"_{int(ts)}", f"{chanDef['ext']}"])
        else:
            fileName = "".join([name, f"_{int(ts)}"])
        if subpath is None:
            return os.path.join(chanDef['subdir'], fileName)
        else:
            return os.path.join(chanDef['subdir'], subpath, fileName)

    def newAbsolutePath(self, channelType, timestamp=None, create=True):
        if timestamp is None:
            timestamp = nowEpoch()
        fName = self.newRelativePath(channelType, timestamp)
        fPath = os.path.join(self.archiver.getArchivePath(timestamp), fName)
        if not os.path.exists(fPath) and create:
            if not os.path.exists(os.path.dirname(fPath)):
                os.makedirs(os.path.dirname(fPath))
            with open(fPath, 'w') as f:
                pass
        return fPath

    # def updateChannel(self, recordTimestamp, Notes, formatter, newRecordFilename):
    def updateChannel(self, ts, channelType, Notes=None, newMetadata=None, newRecordLines=None):
        """Updates the manifests of a channel with new information (metadata, config, etc)"""
        if channelType == ChannelType.Data or channelType == ChannelType.Metadata:
            # need to update the metadata of both data and metadata channeltypes.
            for cType in [ChannelType.Data, ChannelType.Metadata]:
                self._updateManifest(cType,ts, newMetadata, Notes)
        else:
            self._updateManifest(channelType, ts, newMetadata, Notes)
        if newRecordLines:
            ci = self.getChannelInfo(channelType)
            man = ci['manifest']
            rec = man.getManifestRecord(ts)
            for line in newRecordLines:
                rec.formatter.writeRow(line)

    def _updateManifest(self, channelType, timestamp, newMetadata, Notes=None):
        """Used as a helper method by updateChannel to update the lines of a manifest with a new formatter etc."""
        ci = self.getChannelInfo(channelType)
        man = ci['manifest']
        d, t = manEpochToDT(timestamp)
        formatter = CHANNEL_TYPE_MAP[channelType]['formatter'](self.channelName, channelType, newMetadata, self,
                                                             readOnly=self.archiver.isReadonly(), timestamp=timestamp)
        manifestRecord = ManifestRecord(d, t, Notes, formatter)
        man.addManifestRecord(manifestRecord)

    def importManifest(self, channelType, manifestFile):
        with open(manifestFile, 'r') as mf:
            r = csv.DictReader(mf)
            next(r)
            for line in r:
                fName = line['Filename']
                d = line['RecordDate']
                t = line['RecordTime']
                notes = line['Notes']
                fullOGFilename = os.path.abspath(os.path.join(os.path.dirname(manifestFile), fName))
                self._updateManifest(channelType, manDTtoEpoch(d, t), None, notes)
                self.copy(channelType, manDTtoEpoch(d, t), fullOGFilename)

    def getMetadata(self, timestamp=None):
        if ChannelType.Data in self.typeMap.keys():
            man = self.typeMap[ChannelType.Data]['manifest']
            mr = man.getManifestRecord(timestamp)
            if mr:
                try:
                    return mr.formatter.metadata
                except:
                    pass # metadata is not in formatter, so get it from the metadata channel in the fallthrough.
        if ChannelType.Metadata in self.typeMap.keys():
            man = self.typeMap[ChannelType.Metadata]['manifest']
            mr = man.getManifestRecord(timestamp)
            if mr:
                try:
                    return mr.formatter.metadata
                except:
                    return mr.formatter.read()
        else:
            return None

def manDTtoEpoch(date, time):
    if date == 'current' and time == 'current':
        return MAX_EPOCH
    else:
        try:
            dtFormat = " ".join([MAN_DATE_FMT, MAN_TIME_FMT_FRAC])
            manDT = " ".join([date, time])
            dt = datetime.strptime(manDT, dtFormat)
            ts = DTtoEpoch(dt)
            if dt.strftime(dtFormat) == EpochtoDT(MAX_EPOCH).strftime(dtFormat):
                return MAX_EPOCH
            return ts
        except Exception as e:
            dtFormat = " ".join([MAN_DATE_FMT, MAN_TIME_FMT])
            manDT = " ".join([date, time])
            dt = datetime.strptime(manDT, dtFormat)
            ts = DTtoEpoch(dt)
            if dt.strftime(dtFormat) == EpochtoDT(MAX_EPOCH).strftime(dtFormat):
                return MAX_EPOCH
            return ts

def manEpochToDT(ts):
    dt = EpochtoDT(ts)
    date = dt.strftime(MAN_DATE_FMT)
    time = dt.strftime(MAN_TIME_FMT_FRAC)
    return date,time