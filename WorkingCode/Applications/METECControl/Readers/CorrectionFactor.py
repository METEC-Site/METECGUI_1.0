import copy
import queue

from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Commands import CommandClass, CommandMethod
from Framework.BaseClasses.Package import Package
from Framework.BaseClasses.Registration.FrameworkRegistration import FrameworkObject
from Framework.BaseClasses.Subscriber import Subscriber
from Framework.BaseClasses.Worker import Worker
from Utils import FileUtils as fUtils


# TODO:
    # Obtain Correction Factors from configs. Also come up with format/structure for configs.
    # Register Corrected Source with Directory Archiver. (using metadata)

    # PT = Pressure Transducer. Needs translation from raw voltage -> [slope/offset] -> pressure.
    # TC = Thermocouple. Needs no translation from LabJack.
    # EV = Electronic Valve. Needs no translation from LabJack.
    # FM = FlowMeter. Needs translation for the following:
        # Raw Voltage -> [slope/offset] -> uncorrected flow
        # uncorrected flow -> [k factor/k factor reference] -> corrected flow
        # corrected flow -> [GC Data] -> speciation flow.
    # Met Station: Needs slop offset, and also correct ground. Ground from LJ is different than ground pin on Met Station.
        # The correct ground offset is grabbed by the AIN0 pin.

class CorrectionFactor(CommandClass, Subscriber, Worker):
    def __init__(self, archiver=None, commandManager=None, dataManager=None, eventManager=None,
                 name="CorrectionFactor", readerSummary=None, gcSummary = None, **kwargs):
        super().__init__(name=name,
                         archiver=archiver, commandManager=commandManager, dataManager=dataManager, eventManager=eventManager, **kwargs)
        # Subscriber.__init__(self, name, archiver, commandManager, dataManager, eventManager, **kwargs)
        # Worker.__init__(self, archiver, commandManager, dataManager, eventManager, name)
        # ThreadedDestination.__init__(self, name=name)
        # CommandClass.__init__(self, name=name, commandManager=commandManager)
        self.dataManager.subscribe(self)
        self.mdMap = {}
        self.mdGivers = {}
        self.correctionTag = '_corr'

        self._loadGC(gcSummary)
        self._loadReaderSummary(readerSummary)
        self.correctSources = {readerName: True for readerName in self.readerRecords.keys()}

    def _loadReaderSummary(self, readerSummaryFile):
        readerSummary = fUtils.loadSummary(readerSummaryFile)
        latestSummaryTS = sorted(readerSummary)[-1]
        self.readerRecords = readerSummary[latestSummaryTS]["LoadedRecord"]

    def _loadGC(self, gcSummaryFile):
        gcSummary = fUtils.loadSummary(gcSummaryFile)
        latestSummaryTS = sorted(gcSummary)[-1]
        self.gcRecords = gcSummary[latestSummaryTS]["LoadedRecord"]

    def createMDGiver(self, sourceName):
        md = self.getSourceMD(sourceName)
        mdGiver = MDgiver(f'{sourceName}{self.correctionTag}', md, self.commandManager)
        self.mdGivers[sourceName] = mdGiver
        self.archiver.createChannel(f'{sourceName}{self.correctionTag}', ChannelType.Data, metadata=mdGiver.getReaderMetadata())

    def handlePackage(self, package):
        try:
            if package.channelType == ChannelType.Data and not '_corr' in package.source and package.payload and not "MET" in package.source: # adding MET for shanru's 10hz readings, as it was bogging everything down.
                mdGiver = self.mdGivers.get(package.source)
                if not mdGiver:
                    self.createMDGiver(package.source)
                    mdGiver = self.mdGivers.get(package.source)
                if self.correctSources.get(package.source, False):
                    pl = package.payload
                    source, corrPl = self.correctPayload(package.source, pl)
                    pkg = Package(source, payload=corrPl, channelType=ChannelType.Data)
                    sl = list(sorted(corrPl.keys()))
                    if 'source' in sl:
                        sl.remove('source')
                    if list(sorted(mdGiver.getReaderMetadata().keys())) == sl:
                        self.dataManager.accept(pkg)
        except Exception as e:
            self.logger.error(e)

    @CommandMethod
    def correctPayload(self, source, pl):
        correctedPL = {}
        devInfo = self.getInfoFromSource(source)
        for singleFieldName, data in pl.items():
            if singleFieldName == 'source':
                pass
                correctedPL['source'] = f'{data}{self.correctionTag}'
            elif singleFieldName == 'timestamp':
                correctedPL['timestamp'] = data
            else:
                deviceInfo = devInfo[singleFieldName]
                corrMethod = deviceTypes.get(deviceInfo.get('item_type'), CorrectionFactor.noCorrection)
                if corrMethod == CorrectionFactor.metStationCorrection and 'GND' in pl:
                    # met station corrections require a ground offset, since the V on the LJ ground pin is different
                    # than the V of the Met Station Ground Pin.
                    gnd = pl.get('GND', 0)
                    data = data - gnd
                corrData = corrMethod(self, deviceInfo, data)
                correctedPL[f'{singleFieldName}'] = corrData
        return f'{source}{self.correctionTag}', correctedPL

    @CommandMethod
    def getSourceMD(self, source):
        mdReq = self.createCommandPackage('getSourceMD', source, 'getReaderMetadata')
        md = self._emitCommand(mdReq)
        if md:
            return md
        return None

    @CommandMethod
    def getInfoFromSource(self, source):
        if source in self.mdMap:
            return self.mdMap[source]
        mdReq = self.createCommandPackage('getInfoFromSource', source, 'getInfo')
        md = self._emitCommand(mdReq)
        if md:
            self.mdMap[source] = md
            return md
        return None

    def noCorrection(self, deviceInfo, value):
        return value

    def flowmeter(self, deviceInfo, value):
        lj = deviceInfo['reader']
        gsh = lj.split('.')[0]
        gshGCs = self.gcRecords.where(self.gcRecords.gas_house==gsh).dropna(axis=0, how="all")
        if not gshGCs.empty:
            corrGC = gshGCs.iloc[0] # Currently taking the most recent GC record.
            # TODO: grab one corresponding to the datetime
             # for which the fill date matches the GC run date. Also record an event if there is no GC record for that day.
            slope = float(deviceInfo['slope'])
            offset = float(deviceInfo['offset'])
            slpm = value * slope + offset
            kCorrected = slpm * float(corrGC['KLambdaAvg']) # correction factor from N2 to the gas composition of gas.
            return kCorrected
        else:
            return value

    def slopeIntercept(self, deviceInfo, value):
        slope = float(deviceInfo['slope'])
        offset = float(deviceInfo['offset'])
        realValue = value * slope + offset
        return realValue

    def metStationCorrection(self, deviceInfo, value):
        corrVal = self.slopeIntercept(deviceInfo, value)
        return corrVal

class MDgiver(CommandClass, FrameworkObject):
    def __init__(self, name, md, commandManager):
        super().__init__(name=name, commandManager=commandManager)
        self.md = {}
        if not md is None:
            for key, val in copy.deepcopy(md).items():
                self.md[key] = val
        self.inputQ = queue.Queue()
        self.started=False

    def handlePackage(self, package):
        raise NotImplementedError

    @CommandMethod
    def getReaderMetadata(self):
        return self.md


deviceTypes = {
    'Pressure Transducer': CorrectionFactor.slopeIntercept,
    'Flow Meter': CorrectionFactor.flowmeter,
    'Met Station': CorrectionFactor.metStationCorrection,
    'U Wind Speed': CorrectionFactor.metStationCorrection,
    'V Wind Speed': CorrectionFactor.metStationCorrection,
    'W Wind Speed': CorrectionFactor.metStationCorrection,
    'Sonic Temperature': CorrectionFactor.metStationCorrection,
    'Air Temperature': CorrectionFactor.metStationCorrection,
    'Relative Humidity': CorrectionFactor.metStationCorrection,
    'Barometric Pressure': CorrectionFactor.metStationCorrection,
    'Battery Voltage': CorrectionFactor.metStationCorrection
}