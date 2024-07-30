from Applications.METECControl.Readers.LabJack import LabJack
from Applications.METECControl.Readers.LabjackModbusServer import LocalModbusLabjack
from Framework.BaseClasses.Channels import ChannelType
from Utils import FileUtils as fUtils


def LabJackFactory(archiver, commandManager, dataManager, eventManager, readerSummary, fakeServer=False, **kwargs):
    # deviceList = archiver.readConfig('DeviceList')
    # pinsToRegisters = archiver.readConfig('LabJackPinsToRegisters')
    # pinsToDIO = archiver.readConfig('LabJackPinsToDIO')
    # sensorProperties = archiver.readConfig('SensorProperties')

    if fakeServer:
        localModbus = LocalModbusLabjack(archiver)
        localModbus.start()

    readerConfigs = fUtils.loadSummary(readerSummary)
    lastConfigTS = sorted(readerConfigs, key=lambda x: x)[-1]
    modernConfig = readerConfigs[lastConfigTS]

    labjacks = []
    for itemName, itemInfo in modernConfig['LoadedRecord'].items(): # assuming loaded from json.
        if "LJ" in itemName:
            ip = itemInfo['IP']
            fields = itemInfo['fields']
            controller = itemInfo['Controller']
            processGroup = itemInfo['processGroup']
            upstreamGSH = itemInfo['upstreamGSH']
            interval = itemInfo.get('readInterval', 1)  # amount of time to wait before next read.
            singleLJ = LabJack(archiver, commandManager, dataManager, eventManager,
                               name=itemName, IP=ip, fields=fields, controller=controller,
                               processGroup=processGroup, upstreamGSH=upstreamGSH, readInterval=interval)
            labjacks.append(singleLJ)
            archiver.createChannel(singleLJ.getName(), ChannelType.Data, metadata=singleLJ.getReaderMetadata())
    return labjacks