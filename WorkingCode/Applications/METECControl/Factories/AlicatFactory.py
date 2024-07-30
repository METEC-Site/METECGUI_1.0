import Utils.FileUtils as fUtils
from Applications.METECControl.Readers.AlicatMFCReader import AlicatMFCReader
from Framework.BaseClasses.Channels import ChannelType


def AlicatFactory(archiver, commandManager, dataManager, eventManager, readerSummary, **kwargs):
    #
    # deviceList = fUtils.loadCSV('DeviceList', archiver)
    # bitsList = fUtils.loadCSV('AlicatBitToStatus', archiver)
    # pinsList = fUtils.loadCSV('AlicatPins', archiver)
    # fieldList = fUtils.loadCSV('SensorProperties', archiver)

    readerConfigs = fUtils.loadSummary(readerSummary)
    lastConfigTS = sorted(readerConfigs, key=lambda x: x)[-1]
    modernConfig = readerConfigs[lastConfigTS]


    alicats = []
    for acName, itemInfo in modernConfig['LoadedRecord'].items():
        if "FC" in acName:
            totalizer = itemInfo.get('totalizer', False)
            ip = itemInfo['IP']
            fieldList = itemInfo['fields']
            singleAlicat = AlicatMFCReader(archiver, commandManager, dataManager, eventManager, name=acName, IP=ip, deviceType='AlicatMFC', totalizer=totalizer)
            alicats.append(singleAlicat)
            for singleField in fieldList:
                singleAlicat.addDevice(singleField, fieldList[singleField])
            archiver.createChannel(singleAlicat.name, ChannelType.Data, metadata=singleAlicat.getReaderMetadata())
    return alicats