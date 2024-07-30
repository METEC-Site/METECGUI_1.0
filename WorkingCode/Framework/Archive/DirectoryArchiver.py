import logging
import os
import pathlib
import threading
from datetime import datetime

import pandas as pd
from Framework.Archive.ChannelIO import ChannelIO, CHANNEL_TYPE_MAP
from Framework.Archive.GenerateChannelMap import getChannelMap
from Framework.Archive.Logger import LoggingReader
from Framework.Archive.RolloverManager import RolloverManager
from Framework.BaseClasses.Archiver import Archiver
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Destination import ThreadedDestination
from Framework.BaseClasses.Events import EventTypes
from Utils import ClassUtils as cu
from Utils import FileUtils as fUtils
from Utils import TimeUtils as tu
from Utils.TimeUtils import MIN_EPOCH, MAX_EPOCH

"""
.. _directory-archiver:

#################
Directory Archiver
#################

:Authors: Aidan Duggan, Jerry Duggan
:Date: Reviesd January 13, 2020

This module Archives data to a specified directory.

Version: 2.0
Updated to include manifests.
"""
__docformat__ = 'reStructuredText'

VERSIONS = {
    '1': {'configName': 'DA_Config'},
    '2.0': {'configName': 'ArchiveInfo'}
}


DEFAULT_TEMPLATE = "_%Y-%m-%d_%H-%M-%S"
class ChannelExistsError(Exception):
    pass

# todo: load from manifests.
# todo: Test readonly and rollover functionality in unitTests
# todo: keep only the most recent manifest records when roll over.

class RepeaterThread(threading.Thread):
    """ A thread that runs a method on a timer every [interval] seconds.

    In this case, it is used to repeatedly save archive information using the Archiver method _repeatedSave and _rolloverCheck"""
    def __init__(self, stopper, logger, name, target, interval, *args, **kwargs):
        self.logger = logger
        self.__args = args
        self.__kwargs = kwargs
        threading.Thread.__init__(self, name=name)
        self.__method = target
        self.__stopper = stopper
        self.__interval = interval

    def run(self):
        self.logger.debug(f'Starting {self.name} in Directory Archiver.')
        while not self.__stopper.wait(self.__interval):
            self.logger.debug(f'Calling method within thread {self.name}.')
            self.__method(*self.__args, **self.__kwargs)

class DirectoryArchiver(Archiver, ThreadedDestination):
    ''' A class that manages a directory (or set of directories), storing input streams of data, configs, etc in a folder heirarchy.
    '''

    def __init__(self, name='DirectoryArchiver', baseDir=None, template=DEFAULT_TEMPLATE,
                        utcStartHMS = "6:00:00", logConfigFilepath=None,
                        rolloverCriteria='time', rolloverInterval = 86400, checkROInterval = 5,
                        readonly=False,
                        configFiles: list = None, manifests: list = None, originalArchiveDir=None,
                        **kwargs): # todo: do something with utcStartHMS

        # note: the following lines up to _configureLogger should be kept in this order.
        # note again: The above lines were true up until the Framework Object pushes.
        super().__init__(name=name, **kwargs)
        self._configureLogger(name, logConfigFilepath)
        self.ArchiverLock = threading.RLock()
        # ThreadedDestination.__init__(self, name=name, **kwargs)
        # Archiver.__init__(self, name=name)
        self.subThreadStopper = threading.Event()

        if originalArchiveDir:
            baseDir = os.path.split(originalArchiveDir)[0]
        self.initRecord = {
            'name': name,
            'baseDir': baseDir,
            'template': template,
            'utcStartHMS': utcStartHMS,
            'logConfigFilepath': logConfigFilepath,
            'rolloverCriteria': rolloverCriteria,
            'rolloverInterval': rolloverInterval,
            'checkROInterval': checkROInterval,
            'readonly': readonly,
            'configFiles': configFiles,
            'manifests': manifests,
            'originalArchiveDir': originalArchiveDir
        }
        self.readonly = readonly  # marks if the archiver is readonly/should not save any incoming information

        self.archiveStartTS = tu.nowEpoch()
        self.template = template  # template for the name of the archive. Intended to be some datetime format.
        # baseDir: root directory of the archive. When rolling over, this will not change.
        # archivePath: full path of the current archive
        # archiveName: formatted name with the time information placed in the template. Also the last directory in the archivePath.
        if originalArchiveDir:
            # load archiver from original archive directory.
            self.baseDir, self.archivePath, self.archiveName = self._importFromArchive(originalArchiveDir)
        else:
            # create a new archive based on passed input parameters.
            self.baseDir, self.archivePath, self.archiveName = self._setupDirs(template, baseDir) # todo: unify how template is used.
            if not readonly and not os.path.exists(self.archivePath):
                os.makedirs(self.archivePath)

        # self.startTime = self._parseHMS(utcStartHMS)
        self.checkROInterval = int(checkROInterval) # set the rollover interval
        self.archiveConfigName = 'ArchiveInfo' # key/channel name of the archive information.
        self._resetArchiveConfig() # set up internal archive structure, like channelMapping, archiveInfo template, initRecord, etc.

        self.createChannel(self.LR.getName(), ChannelType.Log)
        self.createChannel(self.archiveConfigName, ChannelType.DirConfig)  # create the directory config channel to be saved first.
        # self.startUTCTimestamp = self.archiveStartTS
        joinedStart = f"{datetime.today().year}-{datetime.today().month}-{datetime.today().day} {utcStartHMS}"
        self.startUTCTimestamp = tu.DTtoEpoch(datetime.strptime(joinedStart, "%Y-%m-%d %H:%M:%S"))

        self.rolloverManager = RolloverManager(rolloverCriteria, self.getArchivePath(), rolloverInterval, dirStartTime=self.startUTCTimestamp)

        self._importConfigs(configFiles)
        self._importManifests(manifests) # import external manifests into the archiver.

        # create threads that will run repeatedly on their specified intervals.
        self._setupSubThreads()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

    def _resetArchiveConfig(self):
        self.channelMap = {} # internal mapping of channelName: channelInfo object.
        self.archiveInfo = {
            "archiveVersion": '2.0',
            'start':tu.EpochtoDT(self.archiveStartTS),
            'lastUpdate':tu.nowDT(),
            "archivePath": self.getArchivePath()
            # "size": self._calcSize()
        } # this information will be updated and saved every 5 seconds, as according to the saveThread.
        self.archiveRecord = {"archiveInfo":self.archiveInfo,
                              'initRecord': self.initRecord,
                              "channelMap":self.channelMap} # internal map of this archive's information. Will update to a new key when rolling over.

    def _setupSubThreads(self):
        # todo: scalability testing with the amount of threads.
        self.saveThreadName = f'Archiver\'{self.name}\'-save-thread'
        self.rolloverThreadName = f'Archiver\'{self.name}\'-rollover-thread'
        self.saveThread = RepeaterThread(self.subThreadStopper, self.logger, name=self.saveThreadName, target=self._repeatedSave, interval=5)
        self.rolloverThread = RepeaterThread(self.subThreadStopper, self.logger, name=self.rolloverThreadName, target=self._rolloverCheck, interval=self.checkROInterval)

    def _importFromArchive(self, archiveDirectory):
        if os.path.exists(archiveDirectory):
            baseDir, archiveName = os.path.split(archiveDirectory)
            return baseDir, archiveDirectory, archiveName
        raise FileExistsError(f'Path to specified archive does not exist: {archiveDirectory}')

    def _configureLogger(self, name, loggingConfig):
        self.LR = LoggingReader(archiver=self, commandManager=None, dataManager=None, eventManager=None,
                                logConfigChannelName=loggingConfig, name='_'.join([name, 'logger']))
        self.logger = logging.getLogger(name)

    def getChannels(self):
        cMap = {}
        for channelName, channelIO in self.channelMap.items():
            cMap[channelName] = channelIO
        return cMap

    def getMetadata(self, channel, timestamp=None):
        """ Read the metadata of a channel based on the current timestamp.

        If available, will obtain from the
        DataChannel Formatter metadata (in memory), or will performa a read from Metadata channel
        formatter if unable to get from DataChannel.

        :param channel:
        :param timestamp:
        :return:
        """
        cIO = self.channelMap.get(channel)
        if cIO:
            md = cIO.getMetadata(timestamp)
            return md
        return None

    def start(self):
        if not self.isReadonly():
            self.saveThread.start()
            self.rolloverThread.start()
        ThreadedDestination.start(self)

    def end(self):
        """Method that ends functionality of Archiver. Will stop repeatedly saving as well as checking for rollover. """
        self.logger.info(f'end() method called for Directory Archiver {self.name}')
        with self.ArchiverLock:
            self.subThreadStopper.set()
            self._saveDAConfig()
            self.LR.end()
            ThreadedDestination.end(self)

    def _closeAll(self):
        for channelName, channelIO in self.channelMap.items():
            channelIO.close()

    def getArchiveName(self):
        with self.ArchiverLock:
            return self.archiveName

    def getBasePath(self):
        with self.ArchiverLock:
            return self.baseDir

    def _newArchiveName(self, timestamp=None):
        """ Obtain a new archive name based on the joined self.name, self.template and timestamp using datetime string formatting.

        :param timestamp: Timestamp. If None, then use nowEpoch.
        :return:
        """
        joinedName = "".join([self.name, self.template])
        if timestamp is None:
            time = tu.EpochtoDT(tu.nowEpoch())
        else:
            time = tu.EpochtoDT(timestamp)
        return time.strftime(joinedName)

    def importChannelMap(self, channelMap, overwrite=True):
        """ Import an external channel map and incorporate it into the current channel map."""
        with self.ArchiverLock:
            for channelName, channelConfig in channelMap.items():
                if channelName in self.channelMap:
                    self.logger.debug(f'Channel Named {channelName} already exists in archive channel map.')
                    if overwrite:
                        self.logger.debug(f'Overwriting channel {channelName} with imported channel info. ')
                    else:
                        self.logger.debug(f'Cannot overwrite channel; overwrite set to False')
                        return
                ci = ChannelIO(self, channelName, loggerName=self.logger.name, importConfig=channelConfig, overwrite=True)
                self.channelMap[channelName] = ci

    def _setupDirs(self, template, baseDir):
        """ Helper method that returns the base path of the archive, as well as making a new archive path and name.
        Will ensure the new archive name is unique by adding a timestamp to any conflicting dirNames."""
        baseDir = os.path.abspath(baseDir)
        if template == DEFAULT_TEMPLATE:
            templ = self.name + template
        else:
            templ = template
        # set the current directory, finding a unique name.
        dirName = tu.nowDT().strftime(templ)
        currentDir = os.path.join(baseDir, dirName)
        currentDir = self._addUniqueTag(currentDir)
        baseDir, dirName = os.path.split(currentDir)
        return baseDir, currentDir, dirName

    def _importSingleManifest(self, channelName, channelType, fileName):
        """ Import a channel and its manifest into the archive for record keeping.

        :param channelName: name of channel
        :param channelType: type of channel
        :param fileName: name of original manifest path.
        :return:
        """
        # todo: check this functionality.
        self.createChannel(channelName, channelType, createFirstEntry=False)
        cio = self.channelMap[channelName]
        cio.importManifest(channelType, fileName)

    def _importManifests(self, manifests=None):
        """ Import many manifests from a list. Each manifest should be a {channelName: filename} where filename is a path
        to a manifest file.


        :param manifests:
        :type manifests: list or None
        :return:
        """
        if manifests:
            if type(manifests) == list:
                for singleManifest in manifests:
                    cName = singleManifest['channel']
                    bPath = singleManifest.get('basePath', '')
                    subPath = singleManifest.get('subPath', '')
                    fileName = singleManifest.get('fileName', '')
                    fullPath = os.path.join(bPath, subPath, fileName)
                    self._importSingleManifest(cName, ChannelType.Config, fullPath)
            else:
                raise Exception(f'Could not import manifests: Expecting type (dict)')
        else:
            pass

    def _importConfigs(self, configInfo=None):
        if not configInfo:
            configInfo = []
        for singleConfig in configInfo:
            channelName = singleConfig['channel']
            basePath = singleConfig.get('basePath', '')
            subPath = singleConfig.get('subPath', '')
            fileName = singleConfig.get('fileName', '')
            originalPath = os.path.join(basePath, subPath, fileName)
            self.createChannel(channelName, ChannelType.Config, copyFromPath=originalPath, subPath=subPath, fileName=fileName, createFirstEntry=not(self.readonly))
        self._saveDAConfig()

    def _saveDAConfig(self):
        """ updates the DAConfig.json file with the most up to date time, dir size, and channel infomation

        :return:
        """
        with self.ArchiverLock:
            configCio = self.channelMap[self.archiveConfigName]
            self.archiveInfo['lastUpdate'] = tu.nowDT()
            self.archiveInfo['size'] = self._calcSize()
            if not self.readonly:
                configCio.delete(ChannelType.DirConfig)
                configCio.write(self.archiveRecord, ChannelType.DirConfig)

    def _calcSize(self):
        """Recursively calculate the current size of the directory and all files within the archive. """
        # todo: scalability check on this calcsize method, if it takes too much time to calculate.
        with self.ArchiverLock:
            def size(dir):
                total = 0
                for entry in os.scandir(dir):
                    if os.path.isdir(entry):
                        total += size(entry)
                    elif os.path.isfile(entry):
                        total += os.path.getsize(entry)
                return total
            try:
                return size(self.getArchivePath())
            except Exception as e:
                self.logger.exception(f'Could not calculate the size of the directory due to error {e}')
                return 0

    def _addUniqueTag(self, path):
        """Adds a unique tag to the end of the path/file/dirname if it exists"""
        tag = ""
        tempDir = path
        while os.path.exists(tempDir):
            tag = fUtils.getNextTag(tag)
            tempDir = ''.join([path + tag])
        return tempDir

    def isReadonly(self):
        """Depreciated?..."""
        return self.readonly

    def getArchivePath(self, timestamp=None):
        with self.ArchiverLock:
            return self.archivePath

    def getStartTS(self):
        # todo: should this be the overall archive start (IE object instantiation), or should the ts start over at the rollover?
        # answer: start of current archive.
        return self.archiveStartTS

    def createChannel(self, name, channelType, metadata=None, copyFromPath=None, subPath=None, fileName=None, createFirstEntry=True, timestamp=None):
        """ Create a new channel in the channel map (or adds channelType to the current CHannelIO Object

        # todo: possible error with multiple channels being created on a channel that already exists when receiving a package.
        # todo: Fix error when creating a readonly config channel.

        :param name: name of the channel.
        :param channelType: Type of channel
        :param metadata: Any metadata associated with the channel. Pertinent to DataChannels that have necessary metadata.
        :param copyFromPath: If supplied, will copy this file into the directory archiver.
        :param createFirstEntry: If marked True, will write/create the first file. Otherwise, will wait to receive a package to write the file.
        :param timestamp: The designated timestamp with which this channelType/name combo was created. Defaults to now.
        :return:
        """
        if timestamp is None:
            timestamp = tu.nowEpoch()

        with self.ArchiverLock:
            if metadata and channelType == ChannelType.Data:
                self.createChannel(name, ChannelType.Metadata, metadata, createFirstEntry=createFirstEntry, timestamp=timestamp)
                cio = self.channelMap.get(name)
                cio.write(metadata, ChannelType.Metadata)
            if self.channelMap.get(name) is None:
                self.channelMap[name] = ChannelIO(self, name, self.name)
            ci = self.channelMap[name]
            if not self._channelExists(name, channelType):
                ci.addChannelType(channelType, metadata=metadata, createFirstEntry=createFirstEntry, timestamp=timestamp)
            if copyFromPath:
                if not self.readonly:
                    self.logger.debug(f'Copying file from original path into archiver.')
                    try:
                        ci.copy(channelType, timestamp, copyFromPath, subPath, fileName)
                    except FileExistsError as e:
                        logging.exception(e)
                else:
                    ci.addROFile(name, channelType, metadata, copyFromPath)

    def _channelExists(self, channelName, channelType):
        """Helper method to check if a channel already exists in the ChannelIO object."""
        with self.ArchiverLock:
            if channelName in self.channelMap.keys():
                ci = self.channelMap[channelName]
                if channelType in ci.getChannelTypes():
                    return True
            return False

    def handlePackage(self, package):
        """ Accepts an incoming pacakge and writes it to the archive.

        If the channel doesn't exist, create it. If the

        If the channel is a Log, then turn off logging while this is being written to avoid recursion.

        :param package:
        :return:
        """
        # todo: Change all readers to put metadata in their packages.
        with self.ArchiverLock:
            if not self.readonly:
                try:
                    md = None
                    source = package.source
                    if package.channelType == ChannelType.Command:
                        self._handleCommand(package)
                    if package.channelType == ChannelType.Event:
                        self._handleEvent(package)
                    if package.channelType == ChannelType.Data:
                        md = package.metadata
                    if package.channelType == ChannelType.Metadata and (cu.isMetadata(package.payload) or type(package.payload) is dict):
                        md = {k: type(package.payload[k]) for k in package.payload.keys()}
                    elif package.channelType == ChannelType.Log:
                        self.logger.disabled = True # disabling this as a way to avoid infinite recursion when logging a log.
                    self.createChannel(package.source, channelType=package.channelType, metadata=md, timestamp=package.timestamp)
                    cio = self.channelMap.get(source)
                    cio.write(package)
                except Exception as e:
                    self.logger.error(f'Directory Archiver Encountered an error: {e}')
                finally:
                    self.logger.disabled=False

    def _handleCommand(self, package):
        # todo: flesh this out, see if there is anything that needs to be done here.
        command = package.payload

    def _handleEvent(self, package):
        event = package.payload
        if event.eventType == EventTypes.FileUpdate:
            channelName = event.channelName
            newFilename = event.filename
            if not self._channelExists(channelName, ChannelType.Config): # assuming that only config channels are updated.
                self.createChannel(channelName,ChannelType.Config, copyFromPath=newFilename)
            else:
                if os.path.exists(newFilename):
                    ci = self.channelMap[channelName]
                    ci.updateChannel(event.timestamp, ChannelType.Config, newRecordLines=pd.read_excel(newFilename).to_csv(index=False))
                else:
                    raise FileExistsError(f'Unable to find file at path specified: {newFilename}')

    def _handleData(self, package):
        pass

    def _repeatedSave(self):
        """ Target of the repeated save thread. Will save directory config information every interval."""
        self.logger.debug(f'Dumping Directory Archiver Archive Info...')
        with self.ArchiverLock:
            try:
                    if not self.isTimeToStop(): # isTimeToStop comes from FrameworkObject base class.
                        self._saveDAConfig()
                    else:
                        self._closeAll()
            except Exception as e:
                self.logger.error(f'Error when performing repeated save action on Directory Archiver: {e}')

    def _rolloverCheck(self):
        """ Checks to see if it is time to rollover. If it is, enact the rollover for the archiver. """
        self.logger.debug(f'Checking Rollover for Directory Archiver')
        with self.ArchiverLock:
            rolloverNow = self.rolloverManager.checkRollover()
            if rolloverNow:
                # todo: put exception handling here too.
                self.logger.debug(f'Rollover Manager indicates it is time for rollover. Initiating _rollover method.')
                self._rollover()

    def _rollover(self):
        """
        Create a new directory with the same channels from the previous directory.

        This is intended to provide a way for the directory archiver to create a new directory and copy pertinent
        information (IE configuration information, metadata) from the most recent directory over to the new one.
        This is generally done after checking for a specific constraint (file size is over a limit, or a certain amount
        of time has elapsed). The archiver will close all open files/channels/formatters, log the end time of this
        directory in the DAConfig.json file, create a new directory based on the self.formatter field (guaranteed to be
        unique), and then copy relevant information into this directory. Logging will then resume, with any new
        data/logs/etc streaming into this new directory. This rollover will be reflected in the DAConfig.json file,
        with the new start time being logged.

        :return: None

        .. notes:
            Will not copy the following channel types:
                * Data
                * Index
                * Event
                * Command
                * Response
                * Log

            Will copy the following channel types:
                * Metadata
                * Config
                * DirConfig
                * Other

        """
        # raise NotImplementedError
        # 0?) Empty the queue and handle all incoming packages?
        # 1) update the current directory
        # 2) For each channel in channel map, keep the old archived and take the most recent entries as the first entry into new channelIO objects.
        # 3)
        rolloverStartTS = tu.nowEpoch()
        if not self.readonly:
            with self.ArchiverLock:
                # acquire all the individual locks from the formatters
                locks = []
                for singleChannelIO in self.channelMap.values():
                    locks = [*locks, *singleChannelIO.getLocks()]
                for singleLock in locks:
                    singleLock.acquire()

                # save the current config and its most up to date values.
                self._saveDAConfig()
                # TODO: Add check to see if two channels have the same name.
                # TODO: add functionality that adds config files of sub directories, not sub directories themselves.
                # TODO: test if truly thread safe, test_DARolloverThreadSafe finds x.formatter does not have lock attribute
                # restart means taking metadata from the most recent DA folder (if it exists), and loading in that metadata
                # todo: break up into smaller chunks.
                # get locks
                # save
                # close
                # copy over
                # reopen etc...

                baseDir, newDir, newName = self._setupDirs(self.template, self.baseDir)
                outputDir = newDir
                tag = ''
                while os.path.isdir(outputDir):  # add _char flag
                    tag = fUtils.getNextTag(tag)
                    outputDir = newDir + '_' + tag
                os.makedirs(outputDir)

                self._closeAll()
                newArchiveInfo = {}
                newChannelMap = {}
                self.rolloverManager.setCurrentDir(currentDir=outputDir)
                self.rolloverManager.incrementTime()
                self.archivePath = outputDir
                # todo: copy over latest configs, data channels, etc.
                for channelName, channelIO in self.channelMap.items():
                    newCI = ChannelIO(self, channelName, self.name)
                    newChannelMap[channelName] = newCI # this handles the metadata and data, what about configs?
                    # for channelType in ChannelType:
                    for channelType in channelIO.getChannelTypes():
                        prevMD = channelIO.getMetadata()
                        prevPath = channelIO.getLatestPath(channelType)
                        newCI.addChannelType(channelType, metadata=prevMD, timestamp=rolloverStartTS)
                        if CHANNEL_TYPE_MAP[channelType]['copyover'] and prevPath and os.path.exists(prevPath):
                            newCI.copy(channelType, tu.nowEpoch(), prevPath) # copy the latest path
                self.channelMap = newChannelMap
                self.archiveInfo = newArchiveInfo
                self.archiveRecord['channelMap'] = newChannelMap
                self.archiveRecord['archiveInfo'] = newArchiveInfo
                # self.dumpAllMetadata() # commented because this isn't a method anymore.
                for singleLock in locks:
                    singleLock.release()
                self.archiveInfo['start'] = tu.nowDT()
                self.archiveInfo['lastUpdate'] = tu.nowDT()
                self.archiveInfo['size'] = self._calcSize()
                self._saveDAConfig()

    # todo: break up into 2 read methods, one simple and one more complex.
    #  The simple should assume that there is only one consistent channel/metadata between min and max ts.
    #  The complex should return multiple sets of readings in the case that manTS and maxTS overlap two or more different
    #  manifest/channel periods.
    # todo: make sure that a user can iterate/discover all channel types/channel names etc to be able to read it through an API.
    def read(self, channel, channelType=ChannelType.Data, minTS=MIN_EPOCH, maxTS=MAX_EPOCH, verbose = False, asDF=False, asDask=False):
        """ A method that reads a file from the directory based on the channel type and channel name.

        :param channel:
        :param channelType:
        :param minTS:
        :param maxTS:
        :return:
        """
        channel = self.channelMap.get(channel)
        if not channel is None:
            # return channel.formatter.read(minTS, maxTS)
            if verbose:
                return channel.read(channelType, minTS, maxTS, asDF=asDF, asDask=asDask)
            else:
                allLines = []
                for line in channel.read(channelType, minTS, maxTS, asDF=asDF, asDask=asDask):
                    allLines = [*allLines, line['reading']]
                return allLines

        else:
            return None

    # todo: re-evaluate if this is necessary after changing read.
    def readConfig(self, name, readingTimestamp = MAX_EPOCH):
        self.logger.debug(f'Reading config for timestamp {readingTimestamp}')
        if type(readingTimestamp) is datetime: #convert datetime to epoch
            readingTimestamp = tu.DTtoEpoch(readingTimestamp)
        elif type(readingTimestamp) is float: # assuming float is in epoch time.
            pass
        else:
            self.logger.debug(f'Archiver named {self.name} could not complete readConfig command; readingTimestamp field expecting either epoch (float) or datetime, not {type(readingTimestamp)}')
            raise TypeError(f'Could not complete readConfig command; readingTimestamp field expecting either epoch (float) or datetime, not {type(readingTimestamp)}')
        configs = self.read(name, ChannelType.Config, MIN_EPOCH, MAX_EPOCH, verbose = True)
        if configs:
            cfgInTs = list(filter(lambda x: (x['startTimestamp'] <= readingTimestamp and (x['endTimestamp'] > readingTimestamp)) or (x['endTimestamp'] == MAX_EPOCH and readingTimestamp == MAX_EPOCH), configs))
            if len(cfgInTs) == 1:
                return cfgInTs[0]['reading'] # todo: return this or whole reading?
            elif len(cfgInTs) > 1:
                self.logger.info(f'Multiple configs found when trying to read timestamp {readingTimestamp}, returning the record with latest start time.')
                return sorted(cfgInTs, key=lambda x: x['startTimestamp'])[0]['reading']
            elif len(cfgInTs) == 0:
                self.logger.info(f'No configs found for channel {name} at timestamp {readingTimestamp}')
                # return {'startTimestamp':0, 'endTimestamp':0, 'metadata':None, 'reading':None}
                return None

def daFromArchive(archivePath, name=None, readonly = True, **kwargs):
    if name is None:
        name = pathlib.Path(archivePath).name
    isArchive, version, cfgPath = getArchiveInfo(archivePath)
    # if not isArchive:
    #     raise FileExistsError(f'Could not find path specified: {archivePath}')
    with open(cfgPath) as f:
        cMap = getChannelMap(archivePath)
        archiveConfig = {"archiveInfo": {}, "initRecord": {}, 'channelMap': cMap}
        # try:
        #     archiveConfig = enc.restrictedJSONLoad(f)
        # except json.decoder.JSONDecodeError:
        #     cMap = getChannelMap(archivePath)
        #     archiveConfig = {"archiveInfo": {}, "initRecord": {}, 'channelMap': cMap}
    if version == '1':
        archive = loadVersion1(archiveConfig, name, readonly, archivePath, **kwargs)
        return archive
    elif version == '2.0':
        archive = loadVersion2(archiveConfig, name, readonly, archivePath, **kwargs)
        return archive
    else:
        archive = loadVersion2(archiveConfig, name, readonly, archivePath, **kwargs)
        return archive
        # other versions are not yet supported.
        raise Exception('The only supported versions are 1 and 2.0. Contact programmer to implement newer versions of archivers.')

def loadVersion1(archiveConfig, name, readonly, archivePath, **kwargs):
    # first version uses DA config and has no manifesting
    dirInfo = archiveConfig['DirInfo']
    channels = archiveConfig['Channels']
    mergedKwArgs = {**kwargs, 'name': name, 'readonly': readonly}
    da = DirectoryArchiver(originalArchiveDir=archivePath, **mergedKwArgs)
    da.importChannelMap(channels)
    return da

def loadVersion2(archiveConfig, name, readonly, archivePath, **kwargs):
    # second version uses manifesting
    dirInfo = archiveConfig['archiveInfo']
    inputKwargs = {**kwargs, **{'name': name, 'readonly': readonly}}
    mergedArgs = {**archiveConfig['initRecord'], **inputKwargs, 'originalArchiveDir': archivePath}
    da = DirectoryArchiver(**mergedArgs)
    da.importChannelMap(archiveConfig['channelMap'])
    return da

    # if (archivePath is None) or (not os.path.exists(archivePath)):
    #     raise FileExistsError(f'Could not find the path specified: {archivePath}')
    # baseDir = os.path.dirname(archivePath)
    #
    # da = DirectoryArchiver(name=name, readonly=readOnly, baseDir=baseDir)
    # da.currentDir = archivePath
    # dirConfig = os.path.join(da.currentDir, 'DA_Config.json')
    # with open(dirConfig) as j:
    #     da.DAConfig = enc.restrictedJSONLoads(j)
    # da.channelMap = da.DAConfig['Channels']
    # for channelName, subChannels in da.channelMap.items():
    #     for channelType, channelInfo in subChannels.items():
    #         channelInfo['currentPath'] = da._getPathFromChannel(channelName, channelType, how='relative')
    #         subChannels[channelType] = ChannelInfo(da, **channelInfo)
    # return da

def getArchiveInfo(archivePath):
    """Retrieve the archive information from the archive config (if the config exists).

    Assuming that all cfgs for now are in json. If this changes in the future, so will this method.
    """
    if not os.path.exists(archivePath):
        return (False, False, False)
    files = []
    for fileName in os.listdir(archivePath):
        filePath = os.path.join(archivePath, fileName)
        if os.path.isfile(filePath):
            files.append(filePath)
    if len(files) == 0:
        return (False, False, False)
    # search the files in the root of the archive for the correct config.
    version, versionInfo, cfgPath = getVersion(files)
    return True, version, cfgPath

def getVersion(files):
    """Get the correct version information based on the input files of the root of the archive."""
    version, versionInfo, cfgPath = None, None, None
    for singleFile in files:
        for singleVersion, vInfo in VERSIONS.items():
            cfgName = vInfo['configName']
            if cfgName in os.path.split(singleFile)[1]:
                # this is the correct file, break from the methods and return the correct information.
                versionInfo = VERSIONS[singleVersion]
                version = singleVersion
                break
        if versionInfo:
            cfgPath = singleFile
            break
    return version, versionInfo, cfgPath