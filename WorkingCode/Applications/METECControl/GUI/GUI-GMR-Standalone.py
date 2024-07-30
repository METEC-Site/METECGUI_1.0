import copy
import os

import numpy as np
from Applications.METECControl.GUI.ConfigWrapper import Configs, ConfigWrapper
from Applications.METECControl.GUI.RefactoredWidgets.MetecMainWindow import MainWindow
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Commands import CommandClass, CommandMethod, CommandLevels
from Framework.BaseClasses.Destination import QueuedDestination
from Framework.BaseClasses.Events import EventTypes, EventPayload
from Framework.BaseClasses.Package import Package
from Framework.BaseClasses.Registration.ObjectRegister import Registry
from Framework.BaseClasses.Subscriber import Subscriber
from Framework.BaseClasses.Worker import Worker
from PyQt5 import QtCore as qtc
from Utils import ClassUtils as cu
from Utils import QtUtils as qu
from Utils import TimeUtils as tu
# todo: implement workflow for configs and updating in GUI
#  1) click update
#  2) send event to archiver that config changed (do not change it here!)
#  3) archiver sends event that config either changed successfully or didn't
#  4) Update config from event that is sent by archiver.
from Utils.QtUtils import CustomQTLock, StopThread

INITIAL_ARR_LEN = 86400 # One day of data points at 1 hz.

# todo: pick up with the config manager accessing here. Instead of importing directly from the files, import from the
#  config manager object.
class GUIInterface(Subscriber, Worker, CommandClass, QueuedDestination):

    def __init__(self, archiver=None, commandManager=None, dataManager=None, eventManager=None,
                 name="MainGUI", updateInterval=10, # milliseconds
                 readerSummaryFile=None, epSummaryFile=None, fmSummaryFile=None, gcSummaryFile=None, experimentConfig=None,
                 **kwargs):
        super().__init__(name=name, archiver=archiver, commandManager=commandManager, dataManager=dataManager, eventManager=eventManager, **kwargs)
        # ThreadedDestination.__init__(self, name=name)
        # CommandClass.__init__(self, name=name, commandManager=commandManager)
        # Subscriber.__init__(self, name=name, archiver=archiver,
        #                     commandManager=commandManager, dataManager=dataManager, eventManager=eventManager, **kwargs)
        # Worker.__init__(self, archiver, commandManager, dataManager, eventManager, name)

        self.GUILock = CustomQTLock()
        self.archiver = archiver
        self.sourceMap = {} # maps sourceName: ChannelType: widgets

        self.updateTimer = qtc.QTimer()
        self.updateTimer.timeout.connect(self.update)
        self.updateTimer.setSingleShot(False)
        self.updateInterval = updateInterval
        self.started = False

        self.streamMapping = {}
        self.activeThreads = {}

        self.lockedWidgets = {}
        self.registeredWidgets = {}

        self.gshLock = CustomQTLock()
        self.gshExperiments = {gsh: (None, None) for gsh in range(1,5)}

        dataManager.subscribe(self)

        # load in each necessary config.
        self.configSummaries = {c: None for c in Configs}

        self.configManager = None
        self.setConfigManager()
        self.updateSummaries()

        self.METECGui = MainWindow(self)
        self.configWrapper = ConfigWrapper(self)

    ####################################################################################################################
    ################################# Methods for loading/accessing in external configs ################################
    ####################################################################################################################

    def setConfigManager(self, mgrName="ManifestManager"):
        mgrObj = Registry.getObject(mgrName)
        if self.configManager is None and cu.isManifestManager(mgrObj):
            self.configManager = mgrObj

    def getConfigSummary(self, configKey):
        return self.configManager.getManifest(configKey.value)

    def chooseConfig(self, configKey):
        # popup dialog box with options based on the config chosen.
        # clicking on a specific config changes the currently loaded config to that one
        #    selected config changes
        #    config change event.
        selectedTimestamp = self.configWrapper.chooseConfig(configKey)
        if selectedTimestamp:
            chosenConfig = self.configManager.retrieveRecord(configKey.value, selectedTimestamp)
            configFilename = chosenConfig["Filename"]
            self.selectConfig(configKey, timestamp=selectedTimestamp)
            self.emitConfigChanged(configKey, configFilename)
            return chosenConfig
        return None

    def updateSummaries(self):
        with self.lock:
            for summaryConfig in Configs:
                self.selectConfig(summaryConfig)

    def selectConfig(self, configKey, timestamp=None):
        with self.lock:
            cfgInfo = self.getConfig(configKey, timestamp)
            if cfgInfo:
                self.configSummaries[configKey] = cfgInfo
                self.emitConfigChanged(configKey, cfgInfo["Filename"])
                return cfgInfo["LoadedRecord"]
            return None

    def getConfig(self, configKey, timestamp=None):
        if timestamp is None:
            timestamp = tu.MAX_EPOCH
        return self.configManager.retrieveRecord(configKey.value, timestamp)

    def getSelectedConfig(self, configKey):
        return self.configSummaries[configKey]['SelectedConfig']

    def getResourceLock(self, sourceName):
        pass

    ####################################################################################################################
    ############################## Methods for handling packages, integrating threading. ###############################
    ####################################################################################################################

    def start(self):
        """ Start the QT update functionality of the GUI interface.

        .. note::
            Package handling should not be done in the threading world if it is passed directly to QT objects. Therefore
            the Destination base class should not be called here, and instead custom QT implementation of handlePackage
            has been implemented.
        """
        with self.GUILock:
            if self.started:
                pass
            else:
                self.started=True
                self.updateTimer.start(self.updateInterval)
                self.METECGui.start()
        # ThreadedDestination.start(self)

    def update(self):
        while not self.inputQueue.empty():
            pkg = self.inputQueue.get()
            try:
                self.handlePackage(pkg)
            except Exception as e:
                self.logger.error(f'GUI Interface could not handle package {pkg} due to exception {e}')
        # self.updateTimer.start(self.updateInterval)

    def handlePackage(self, package):
        """Custom implementation of the handle package method. Takes a package"""
        channelType = package.channelType
        if channelType == ChannelType.Data:
            self._handleData(package)
        elif channelType == ChannelType.Response:
            pass
        elif channelType == ChannelType.Event:
            self._handleEvent(package) # handle package locally

        self.forwardPackage(package)  # passes package to all subscribed widgets

    def forwardPackage(self, package):
        sourceName = package.source
        chanType = package.channelType
        channelSignal = self.getChannelSignal(sourceName, chanType)
        channelSignal.emitPackage(package)

    def _handleEvent(self, eventPackage):
        # todo: put code for handling event from archiver here.
        # likely needed in event payload: channelName, newFilepath?, success message
        if eventPackage.payload.eventType == EventTypes.FileUpdate:
            payload = eventPackage.payload
            config = payload.get('config')
            if config == Configs.FMconfig:
                self.METECGui.fmConfigUpdated.emit(payload.get('filepath'))
            elif config == Configs.EPConfig:
                self.METECGui.epConfigUpdated.emit(payload.get('filepath'))

    def _handleData(self, package):
        if not self.isSourceRegistered(package.source):
            self.initializeSource(package.source)
        if not package.payload:
            return

        # todo: what if metadata changes?
        # grab the metadata for the type of the field so that field registration can get it if necessary.
        sourceInfo = self.getSourceInfo(package.source)
        md = sourceInfo['metadata'] if sourceInfo else None
        if md is None:
            md = package.metadata
            if md is None:
                md = self.getSourceMetadata(package.source)
        if not md is None and not sourceInfo is None:
            sourceInfo['metadata'] = md

        with self.getThreadLock(package.source):
            if sourceInfo['initialized']:
                self.incrementIndex(package.source)
            # iterate through the payload, initializing keys if necessary and adding values to the array.

            # copy the payload so that we can make changes if necessary.
            pldCopy = copy.deepcopy(package.payload)
            if not 'timestamp' in pldCopy:
                pldCopy['timestamp'] = tu.nowEpoch()

            for key, val in pldCopy.items():
                # set metadata for the field and register it if it isn't already.
                if not self.isFieldRegistered(package.source, key):
                    try:
                        fieldType = md[key]
                        if 'type' in fieldType:
                            fieldType = fieldType['type']
                        if not type(fieldType) is type:
                            raise TypeError(f'Expecting type of fieldType to be a type (must be castable)')
                    except Exception as e:
                        fieldType = type(pldCopy[key])
                    self.initializeField(package.source, fieldName=key, fieldType=fieldType)

                # Add data to the growing np array.
                startIndex, endIndex = self.getIndex(package.source)
                npArray = sourceInfo['fields'][key]['array']
                npArray[endIndex] = val

            # successfully added values to the growing array and made sure all fields were initialized. Increment the index
            # if the source has been initialized, or set initialized to True (important for addressing purposes).
            if sourceInfo['initialized']:
                pass
            else:
                sourceInfo['initialized'] = True

    ####################################################################################################################
    ################################# Methods for locking/unlocking resources via GUI. #################################
    ####################################################################################################################

    def obtainLocks(self, **kwargs):
        # resourceallocator.obtainLock()
        # todo: remove below after resourceallocator is added.
        pl = EventPayload(source="CB-1W.LJ-1", eventType=EventTypes.LockWidget, objReqLock="TestManager",
                          controllerName="CB-1W.LJ-1", state=True)
        pkg = Package(source=self.getName(), payload=pl, channelType=ChannelType.Event)
        self.accept(pkg)
        return True

    def releaseLocks(self, resources):
        # resoruceallocator.releaseLocks()
        return True

    def checkLocked(self, resource):
        ...  # resourceAllocator.checkLocked(self.getName(), resource)
        return False

    def getGSHLock(self, gashouse, widgetName, experimentID):
        with self.gshLock:
            currentName, currentExperiment = self.gshExperiments.get(gashouse, (None, None))
            if currentName is None and currentExperiment is None:
                self.gshExperiments[gashouse] = (widgetName, experimentID)
            return currentName, currentExperiment

    def checkGSHLock(self, gashouse):
        name, experiment = self.gshExperiments[gashouse]
        return name, experiment

    def releaseGSHLock(self, gashouse, widgetName, experimentID):
        with self.gshLock:
            if self.gshExperiments[gashouse] == (widgetName, experimentID):
                self.gshExperiments[gashouse] = (None, None)

    ####################################################################################################################
    ################################ Methods for loading in sources/managing np arrays. ################################
    ####################################################################################################################

    def getChannelSignal(self, sourceName, channelType):
        sourceInfo = self.getSourceInfo(sourceName)
        if not sourceInfo:
            self.initializeSource(sourceName=sourceName)
            sourceInfo = self.getSourceInfo(sourceName=sourceName)
        channelSignal = sourceInfo['channelSignals'][channelType]
        return channelSignal

    def subscribeWidget(self, widget, sourceName, channelType):
        """
        Here, stream is a dictionary defined by two parts: a 'sourceName', and a 'channelType'
        """
        if not self.isSourceRegistered(sourceName):
            self.initializeSource(sourceName=sourceName)
        channelSignal = self.getChannelSignal(sourceName, channelType)
        channelSignal.addWidget(widget)

    def isSourceRegistered(self, sourceName):
        if not self.sourceMap.get(sourceName, None):
            return False
        return True

    def isFieldRegistered(self, sourceName, fieldName):
        if self.isSourceRegistered(sourceName) and self.getSourceInfo(sourceName).get('fields',{}).get(fieldName):
            return True
        return False

    def getSourceInfo(self, sourceName):
        if self.isSourceRegistered(sourceName):
            return self.sourceMap[sourceName]
        return None

    def initializeSource(self, sourceName, override=False):
        with self.GUILock:
            if not self.isSourceRegistered(sourceName) or override:
                thisSource = self.sourceMap[sourceName] = {}
                # note: the offest/indexing pertains to the incoming data packets.
                thisSource['startIndex'] = 0
                thisSource['endIndex'] = 0
                thisSource['incrementStart'] = False
                thisSource['initialized'] = False
                thisSource['fields'] = {}
                thisSource['metadata'] = None
                thisSource['resourceLock'] = self.getResourceLock(sourceName)
                # thisSource['threadLock'] = threading.RLock() # commented this out to see if QMutex is better with QT.
                thisSource['threadLock'] = CustomQTLock()
                thisSource['channelSignals'] = {}
                for chan in ChannelType:
                    thisSource['channelSignals'][chan] = PackageToWidgetSignaller()
                self.initializeField(sourceName, 'timestamp')

    def initializeField(self, sourceName, fieldName, fieldType=float, override=False):
        with self.GUILock:
            if not self.isSourceRegistered(sourceName):
                self.initializeSource(sourceName)
            thisSource = self.getSourceInfo(sourceName)
            if self.isFieldRegistered(sourceName, fieldName) and not override:
                raise Exception(f'field named {fieldName} already exists in source map for {sourceName} and override is set to False.')
            thisSource['fields'][fieldName] = {
                'type': fieldType,
                'array': np.zeros(INITIAL_ARR_LEN, dtype=np.dtype(fieldType))
            }

    def getThreadLock(self, sourceName):
        if not self.isSourceRegistered(sourceName):
            return None
        lock = self.getSourceInfo(sourceName)['threadLock']
        return lock

    def getIndex(self, sourceName):
        if not self.isSourceRegistered(sourceName):
            return None
        with self.getThreadLock(sourceName):
            startIndex = self.sourceMap[sourceName]['startIndex']
            endIndex = self.sourceMap[sourceName]['endIndex']
            return startIndex, endIndex

    def setIndex(self, sourceName, startI=None, endI=None):
        lock = self.getThreadLock(sourceName)
        with lock:
            if not startI is None:
                self.sourceMap[sourceName]['startIndex'] = startI % INITIAL_ARR_LEN
            if not endI is None:
                self.sourceMap[sourceName]['endIndex'] = endI % INITIAL_ARR_LEN

    def incrementIndex(self, sourceName):
        sourceInfo = self.sourceMap[sourceName]
        lock = self.getThreadLock(sourceName)
        with lock:
            startIndex = sourceInfo['startIndex']
            endIndex = sourceInfo['endIndex']
            self.setIndex(sourceName, endI=endIndex + 1)
            if endIndex == INITIAL_ARR_LEN-1:
                sourceInfo['incrementStart'] = True
            incrementStart = sourceInfo['incrementStart']
            if incrementStart:
                self.setIndex(sourceName, startI=startIndex + 1)

    def getAllValues(self, sourceName, fieldName):
        if not self.isFieldRegistered(sourceName, fieldName):
            self.initializeField(sourceName, fieldName)
        with self.getThreadLock(sourceName):
            startIndex, endIndex = self.getIndex(sourceName)
            fullXVal = self.sourceMap[sourceName]['fields'][fieldName]['array']
            if endIndex < startIndex:
                fullXVal = np.concatenate((fullXVal[startIndex:INITIAL_ARR_LEN], fullXVal[0:startIndex]))
            elif endIndex == startIndex and endIndex == 0:
                fullXVal = fullXVal[0:0]
            else:
                fullXVal = fullXVal[startIndex:endIndex + 1]
            return fullXVal

    def getFieldValues(self, sourceName, fieldName, startT=None, endT=None):
        if not self.isFieldRegistered(sourceName, fieldName):
            self.initializeField(sourceName, fieldName)
        try:
            # gets the field values from between time startT and endT, including the offset (if there is any).
            if startT is None:
                startT = tu.MIN_EPOCH
            if endT is None:
                endT = tu.MAX_EPOCH

            lock = self.getThreadLock(sourceName)
            with lock:
                fullXVal = self.getAllValues(sourceName, fieldName)
                fullXts = self.getAllValues(sourceName, 'timestamp')

                xStartI = np.where(fullXts >= startT)[
                    0]  # NOTE: This assumes that all incoming values are MONOTONICALLY INCREASING.
                if len(xStartI) > 0:
                    xStartI = xStartI[0]
                else:
                    xStartI = None
                xEndI = np.where(fullXts <= endT)[0]
                if len(xEndI) > 0:
                    xEndI = xEndI[-1] + 1
                else:
                    xEndI = 0

                if xStartI == None:
                    xStartI = xEndI

                xData = fullXVal[xStartI:xEndI]
                xTimestamp = fullXts[xStartI:xEndI]
                return xTimestamp, xData
        except Exception as e:
            self.logger.exception(f'Could not get values for source:field {sourceName}:{fieldName} from timestamp {startT}:{endT} due to an error.')

    def getLatestValue(self, sourceName, fieldName):
        if not self.isFieldRegistered(sourceName, fieldName):
            self.initializeField(sourceName, fieldName)
        sourceInfo = self.getSourceInfo(sourceName)
        with self.getThreadLock(sourceName):
            startIndex, endIndex = self.getIndex(sourceName)
            val = sourceInfo['fields'][fieldName]['array'][endIndex]
            timestamp = sourceInfo['fields']['timestamp']['array'][endIndex]
            return timestamp, val

    ####################################################################################################################
    ################################ Methods for communicating externally to Framework. ################################
    ####################################################################################################################

    def emitEvent(self, eventPkg):
        self.eventManager.accept(eventPkg)

    def emitExperimentConfirmation(self, expNum, confDict):
        event = EventPayload(source=self.getName(), eventType=EventTypes.Annotation, msg=f'Experiment ID {expNum} confirmed by operator', confirmation=confDict)
        eventPkg = Package(source=self.getName(), payload=event, channelType=ChannelType.Event)
        self.emitEvent(eventPkg)

    def emitConfigChanged(self, configKey, filename):
        """
        config: enum for which config is changing. See Configs enum.
        filename: full path to new config file
        """
        event = EventPayload(source=self.getName(), eventType=EventTypes.FileUpdate, msg=f'GUI started using a different {configKey.value}, sourced from file {filename}', config=configKey, filename=filename)
        eventPkg = Package(source=self.getName(), payload=event, channelType=ChannelType.Event)
        self.emitEvent(eventPkg)

    def emitEmissionEvent(self, expID, emission):
        event = EventPayload(source=self.getName(), eventType=EventTypes.Emission, msg='Emission Event', expID=expID, **emission)
        eventPkg = Package(source=self.getName(), payload=event, channelType=ChannelType.Event)
        self.emitEvent(eventPkg)

    def emitExpStart(self, expID, gasHouse, jsonScript, **kwargs):
        event = EventPayload(source=self.getName(), eventType=EventTypes.ExperimentStart, msg='Experiment Started', expID=expID, gasHouse=gasHouse, script=jsonScript, **kwargs)
        eventPkg = Package(source=self.getName(), payload=event, channelType=ChannelType.Event)
        self.emitEvent(eventPkg)

    def emitExpEnd(self, expID, gasHouse, **kwargs):
        event = EventPayload(source=self.getName(), eventType=EventTypes.ExperimentEnd, msg='Experiment Ended',
                             expID=expID, gasHouse=gasHouse, **kwargs)
        eventPkg = Package(source=self.getName(), payload=event, channelType=ChannelType.Event)
        self.emitEvent(eventPkg)

    def emitCalStart(self, expID, gasHouse):
        event = EventPayload(source=self.getName(), eventType=EventTypes.CalStart, msg='Calibration Period started',
                             expID=expID, gasHouse=gasHouse)
        eventPkg = Package(source=self.getName(), payload=event, channelType=ChannelType.Event)
        self.emitEvent(eventPkg)

    def emitCalEnd(self, expID, gasHouse):
        event = EventPayload(source=self.getName(), eventType=EventTypes.CalEnd, msg='Calibration Period ended',
                             expID=expID, gasHouse=gasHouse)
        eventPkg = Package(source=self.getName(), payload=event, channelType=ChannelType.Event)
        self.emitEvent(eventPkg)

    def emitMainStart(self, expID, gasHouse):
        event = EventPayload(source=self.getName(), eventType=EventTypes.MainStart, msg='Starting Main Period', expID=expID, gasHouse=gasHouse)
        eventPkg = Package(source=self.getName(), payload=event, channelType=ChannelType.Event)
        self.emitEvent(eventPkg)

    def emitMainEnd(self, expID, gasHouse):
        event = EventPayload(source=self.getName(), eventType=EventTypes.MainEnd, msg='Ending Main Period', expID=expID, gasHouse=gasHouse)
        eventPkg = Package(source=self.getName(), payload=event, channelType=ChannelType.Event)
        self.emitEvent(eventPkg)

    def onWindowClose(self):
        # called when the window closes.
        msg = 'GUI Interface main window closed - sending shutdown signal.'
        self.logger.info('GUI Interface main window closed - sending shutdown signal.')
        event = EventPayload(self.getName(), eventType=EventTypes.Shutdown, msg=msg)
        eventPackage = Package(self.getName(), payload=event, channelType=ChannelType.Event)
        self.eventManager.accept(eventPackage)

    @CommandMethod
    def shutdownDevice(self, devName):
        # expecting process to be a singular item (str)
        # comPkg = self.createCommandPackage('shutdownProcessGroup', devName, 'eStop', [], {}, commandLevel=CommandLevels.Noncritical)
        comPkg = self.createCommandPackage('shutdownDevice', devName, 'eStop', [], {},
                                           commandLevel=CommandLevels.Noncritical)
        self._emitCommand(comPkg, timeout=.01)

    @CommandMethod
    def closeValve(self, commandDest, args=[], kwargs={}):
        comPkg = self.createCommandPackage('closeValve', commandDest, 'closeValve', args, kwargs)
        return self._emitCommand(comPkg, timeout=.01)

    @CommandMethod
    def closeAllValves(self, commandDest, args=[], kwargs={}):
        comPkg = self.createCommandPackage('closeAllValves', commandDest, 'closeAllValves', args, kwargs)
        return self._emitCommand(comPkg, timeout=.01)

    @CommandMethod
    def openValve(self, commandDest, args=[], kwargs={}):
        comPkg = self.createCommandPackage('openValve', commandDest, 'openValve', args, kwargs)
        return self._emitCommand(comPkg,timeout=.01)

    @CommandMethod
    def getSourceInfoCommand(self, commandDest, args=[], kwargs={}):
        comPkg = self.createCommandPackage('getSourceInfoCommand', commandDest, 'getInfo', args, kwargs)
        sourceInfo = self._emitCommand(comPkg)
        if not type(sourceInfo) is dict:
            sourceInfo = {}
        return sourceInfo

    @CommandMethod
    def getSourceMetadata(self, commandDest, args=[], kwargs={}):
        mdPkg = self.createCommandPackage('getSourceMetadata', commandDest, 'getReaderMetadata', args, kwargs)
        metadata = self._emitCommand(mdPkg)
        if not type(metadata) is dict:
            metadata = {}
        return metadata

    @CommandMethod
    def setSetpoint(self, commandDest, args=[], kwargs={}):
        comPkg = self.createCommandPackage('setSetpoint', commandDest, 'setSetpoint', args, kwargs)
        return self._emitCommand(comPkg, timeout=.01)

    @CommandMethod
    def shutdownProcessGroup(self, process):
        # todo: fix this method!
        stopThreads = []
        for readerName, readerInfo in self.getSelectedConfig(Configs.ReaderConfig).items():
            devProcesses = readerInfo['processGroup']
            devProcesses = devProcesses.split('/')
            if process in devProcesses:
                stopThreads.append(StopThread(self.shutdownDevice, [readerName], self.activeThreads))
        for singleThread in stopThreads:
            self.activeThreads[singleThread] = True
            singleThread.start()


class PackageToWidgetSignaller(qtc.QObject):
    packageReceived = qtc.pyqtSignal(Package)

    def __init__(self):
        qtc.QObject.__init__(self, None)
        self.widgets = set()

    def addWidget(self, widget):
        self.widgets.add(widget)

    def emitPackage(self, package):
        self.packageReceived.emit(package)


def main():
    sensorPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Config/SiteMetadata/SiteConfig_Feb2020.csv'))
    devicePath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Config/SiteMetadata/device_list.csv'))
    epPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Config/Example Configs/ExampleEPConfig_20200428000000.xlsx'))
    fmPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Config/Example Configs/FlowMeterConfig20190701080000.xlsx'))

    gui = GUIInterface(None, None, None, None, readerFieldsRecord=sensorPath, readerList=devicePath, fmConfig=fmPath, epConfig=epPath)

    appStarter = qu.StartApp()
    appStarter.start()

if __name__ == '__main__':
    main()