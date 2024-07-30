import csv
import json
import os

from Framework.BaseClasses.Channels import ChannelType as ct
from Utils import TimeUtils as tu

folderKeys = {ct.Data: 'data', ct.Event: 'events', ct.Metadata: 'metadata', ct.Config:'config', ct.Command:'commands', ct.Log:'logs', ct.Manifest: "manifests"}

def mdFromManifest(manifestPath, metadataPath, longChannel):
    raise NotImplementedError
    chanMDManPath = os.path.join(manifestPath, 'metadata', '.'.join([longChannel, "manifest"]))
    with open(chanMDManPath) as mp:
        rdr = csv.DictReader(mp)
        for line in rdr:
            if longChannel in line['Filename']:
                channelJson = line['Filename']
                mdPath = os.path.join(metadataPath, channelJson)
                try:
                    with open(mdPath) as f:
                        metadata = json.load(f)
                    return mdPath, metadata
                except Exception as e:
                    return mdPath, None
    return None, None

def mdFromFile(metadataPath, longChannel):
    chanMDManPath = os.path.join(metadataPath, '.'.join([longChannel,"json"]))
    try:
        with open(chanMDManPath) as f:
            metadata = json.load(f)
        return chanMDManPath, metadata
    except Exception as e:
        return chanMDManPath, None

def makeMapFromManifests(archivePath):
    raise NotImplementedError

def chanMapFromArchInfo(archivePath):
    raise NotImplementedError

def manifestsExist(archivePath):
    raise NotImplementedError

def preExistingChanMap(archivePath):
    raise NotImplementedError

def addLineToManifest(manList, md, fileName, startTS):
    startDate, startTime = tu.EpochtoDT(startTS).strftime('%m/%d/%Y-%H:%M:%S').split('-')
    if len(manList) > 0:
        recentRec = manList[-1]
        recentRec['EndDate'] = startDate
        recentRec['EndTime'] = startTime
    rec = {"RecordDate": startDate,
         "RecordTime": startTime,
         "EndDate": "12/31/9999",
         "EndTime": "23:59:59",
         "Formatter": {
             "metadata": md,
             "path": fileName
         }}
    manList.append(rec)


def makeMapFromFiles(archivePath):
    archStart = tu.MIN_EPOCH
    folderTypes = {k: {"name": folderKeys[k], 'path': os.path.join(os.path.abspath(os.path.join(archivePath, folderKeys[k])))} for k in folderKeys}
    manifestPath = folderTypes[ct.Manifest]['path']
    channelMap = {}

    for channelType, channelFolder in folderTypes.items():
        folderPath = channelFolder['path']
        for file in os.listdir(folderPath):
            fileName = os.path.join(folderPath, file)
            longChannel, ext = os.path.splitext(file)
            if "idx" in ext:
                continue # skip any file extensions with "idx" in them.

            try:
                # parse the channel name from the file name, using "_" as the separator. Expecting timestamp to be the last value.
                chanPieces = longChannel.split('_')
                startTS = chanPieces[-1]
                chanPieces.remove(startTS)
                startTS = float(startTS)
                channelName = "_".join(chanPieces)
            except ValueError:
                # no timestamp is on this file.
                channelName = longChannel
                startTS = archStart

            if not channelName in channelMap:
                channelMap[channelName] = {"channelName": channelName, "typeMap": {}}

            # add the manifest to the type map if it isn't already there.
            tMap = channelMap[channelName]['typeMap']
            if not channelType in tMap:
                tMap[channelType] = {"manifest":
                                         {"manifestPath": os.path.join(manifestPath, ".".join([channelName,'manifest'])),
                                          "_manifest":[]}
                                     }

            metadataPath = folderTypes[ct.Metadata]['path']
            mdFilepath, md = mdFromFile(metadataPath, longChannel)
            addLineToManifest(tMap[channelType]['manifest']['_manifest'], md, fileName, startTS)
    return channelMap

def getChannelMap(archivePath):
    # if preExistingChanMap(archivePath):
    #     chanMap = chanMapFromArchInfo(archivePath)
    # elif manifestsExist(archivePath):
    #     chanMap = makeMapFromManifests(archivePath)
    # else:
    chanMap = makeMapFromFiles(archivePath)
    return chanMap
