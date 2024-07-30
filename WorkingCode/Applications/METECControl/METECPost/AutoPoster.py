import datetime
import pathlib
import time
import os
import shutil
import logging
from logging import config
import json
from Applications.METECControl.METECPost import METECPost
from Utils import TimeUtils as tu


archiveRootFolder = pathlib.Path("C:\METEC\SiteData\GUI")
finishedPostedFolder = pathlib.Path("R:\_Archives")
finishedUnpostedFolder = pathlib.Path("R:\_RawData\GUI")
archiveLogFile = pathlib.Path("C:\METEC\SiteData\GUI\ArchivePostLogger.log")
archiveLogConfig = pathlib.Path("./PostLoggerConfig.json")

BEING_ADDED_TO_TIME = 4 # seconds
TIMEDELTA_CHECK_THRESHOLD = 60 #3600 # seconds
TENTATIVE_POST_ARCHIVES = {
    'example': {
        'path': None,
        "modDictAtTimeOfCheck": {None: None},
        'epochTimeChecked': 0.0
    }
}

defaultArgs = {
    "archive":None,
    "gc": "C:\\Users\\METEC\\Documents\\SVN_METEC\\Operations\\ConfigurationAndCalibrationRecords\\GasCompositions\\GCRecords\\GasCompositionSummary.csv",
    "rManifest": "C:\\Users\\METEC\\Documents\\SVN_METEC\\Operations\\ConfigurationAndCalibrationRecords\\ReaderRecords\\ReaderSummary.csv",
    "epManifest": "C:\\Users\\METEC\\Documents\\SVN_METEC\\Operations\\ConfigurationAndCalibrationRecords\\EmissionPointConfigurations\\EPConfigSummary.csv",
    "fmManifest": "C:\\Users\\METEC\\Documents\\SVN_METEC\\Operations\\ConfigurationAndCalibrationRecords\\FlowMeterConfigurations\\FMConfigSummary.csv",
    "minSettlingTime": 120
}

def getSubfilesModTimes(folderPath, recursiveModDict=None):
    if recursiveModDict is None:
        recursiveModDict = {}
    for subFolder in folderPath.iterdir():
        if subFolder.is_file():
            recursiveModDict[subFolder.name] = os.path.getmtime(subFolder)
        else:
            getSubfilesModTimes(subFolder, recursiveModDict)
    return recursiveModDict

def isBeingAddedTo(archivePath):
    initialModDict = getSubfilesModTimes(archivePath)
    time.sleep(BEING_ADDED_TO_TIME)
    laterModDict = getSubfilesModTimes(archivePath)
    initialKeys = list(initialModDict.keys())
    laterKeys = list(laterModDict.keys())
    if not initialKeys == laterKeys:
        return True
    for key in initialKeys:
        if not initialModDict[key] == laterModDict[key]:
            return True
    return False

def initLogger():
    with open(archiveLogConfig) as f:
        loggerConfig = json.load(f)
    logging.config.dictConfig(loggerConfig)
    return logging.getLogger('thisFileLogger')

def postProcess(archivePath):
    thisArchiveArgs = {**defaultArgs}
    thisArchiveArgs['archive'] = archivePath
    METECPost.main(**thisArchiveArgs, overrideLoggerLevel=False)

def moveArchive(archivePath, destinationFolder):
    shutil.move(str(archivePath), str(destinationFolder))

def flagCheckForLaterPosting(archivePath):
    archiveName = archivePath.name
    now = tu.nowEpoch()
    modDict = getSubfilesModTimes(archivePath)
    if not isCheckedForLaterPosting(archivePath):
        TENTATIVE_POST_ARCHIVES[archiveName] = {
            "path": archivePath,
            "modDictAtTimeOfCheck": modDict,
            "epochTimeChecked": now
        }

def removeFromCheckForLaterPosting(archivePath):
    archiveName = archivePath.name
    if isCheckedForLaterPosting(archivePath):
        TENTATIVE_POST_ARCHIVES.pop(archiveName)

def isCheckedForLaterPosting(archivePath):
    return not TENTATIVE_POST_ARCHIVES.get(archivePath.name, None) is None

def exceedsTimedeltaCheck(archivePath):
    if not isCheckedForLaterPosting(archivePath):
        return False
    else:
        curTime = tu.nowEpoch()
        thenTime = TENTATIVE_POST_ARCHIVES[archivePath.name]['epochTimeChecked']
        return (curTime-thenTime) >= TIMEDELTA_CHECK_THRESHOLD

def hasNotChanged(archivePath):
    if not isCheckedForLaterPosting(archivePath):
        return False
    currentModDict = getSubfilesModTimes(archivePath)
    oldModDict = TENTATIVE_POST_ARCHIVES[archivePath.name]['modDictAtTimeOfCheck']
    oldKeyList = sorted(list(oldModDict.keys()))
    currentKeyList = sorted(list(currentModDict.keys()))
    if not oldKeyList == currentKeyList:
        return False
    for singleKey in oldModDict.keys():
        if not oldModDict[singleKey] == currentModDict[singleKey]:
            return False
    return True

def main():
    postLogger = initLogger()

    postedArchives = []
    markedAsCurrentlyProcessing = []

    while True:
        archivePaths = list(archiveRootFolder.iterdir())
        archivePaths = sorted(list(filter(lambda x: x.name != archiveLogFile.name, archivePaths)), key = lambda x: x.name)
        for singlePath in archivePaths:
            if not singlePath.name in postedArchives:
                try:
                    tentativeOkToPost = not isBeingAddedTo(singlePath)
                except Exception as e:
                    tentativeOkToPost = False
                if tentativeOkToPost:
                    if singlePath.name in markedAsCurrentlyProcessing:
                        markedAsCurrentlyProcessing.remove(singlePath.name)
                    if not isCheckedForLaterPosting(singlePath):
                        postLogger.info(f"File {singlePath.name} is tentatively ready for posting.")
                        flagCheckForLaterPosting(singlePath)
                    elif isCheckedForLaterPosting(singlePath):
                        if isBeingAddedTo(singlePath):
                            # not ready for posting, remove from the tentative list of files to post process.
                            removeFromCheckForLaterPosting(singlePath)
                        elif exceedsTimedeltaCheck(singlePath) and hasNotChanged(singlePath):
                            try:
                                postProcess(singlePath)
                                moveArchive(singlePath, finishedPostedFolder)
                                postedArchives.append(singlePath.name)
                                removeFromCheckForLaterPosting(singlePath)
                                postLogger.info(f"File {singlePath.name} has been posted.")
                            except Exception as e:
                                moveArchive(singlePath, finishedUnpostedFolder)
                                postLogger.error(f'File {singlePath.name} could not be posted. Instead it has been moved to the folder {finishedUnpostedFolder} '
                                                 f'due to exception {e}')

                elif singlePath.name not in markedAsCurrentlyProcessing:
                    postLogger.info(f"File {singlePath.name} is still being added to. Will not post process yet.")
                    markedAsCurrentlyProcessing.append(singlePath.name)


if __name__ == '__main__':
    main()