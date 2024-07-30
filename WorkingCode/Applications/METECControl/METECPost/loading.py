import logging
import pathlib
import shutil
import os
import tempfile

import pandas as pd
import numpy as np
from dask import dataframe as dd
import datetime
from functools import reduce
import gc

from numpy.compat import os_PathLike

from Framework.Archive.DirectoryArchiver import daFromArchive
from Framework.BaseClasses.Channels import ChannelType
from Utils import TimeUtils as tu
from Utils import FileUtils as fUtils
from Applications.METECControl.Resources.GasChromatography import GCSummary
from Applications.METECControl.METECPost.Corrections import normalizeReaderRecordNames
from Applications.METECControl.METECPost import Helpers as hp

N_PARTITIONS = 1
PARTITION_SIZE = "1000MB"

tempFilePath = pathlib.Path(__file__).parent.joinpath('tempFiles')
fileByChannelPath = tempFilePath.joinpath('channels')
unifiedCompletePath = tempFilePath.joinpath('complete')

class TimeParseError(Exception):
    pass

def isCorrected(channelName):
    if 'corr' in channelName:
        return True
    return False

def mergePDDfs(pdDFs):
    # note that this requires the pandas dfs to be aligned!!!
    # assuming fully aligned dataframes.
    finalDF = None
    for chanName, singleDF in pdDFs.items():
        if finalDF is None:
            finalDF = singleDF.copy(deep=True)
        else:
            for col in singleDF.columns:
                finalDF[col] = singleDF[col]
            # finalDF = pd.merge(df, singleDF, how='outer', left_index=True, right_index=True)
            # finalDF = finalDF.bfill(axis=0, limit=2)
    return finalDF

def alignPDDfs(pdDFs):
    ixDF = None
    alignedDFs = {}
    for chanName, singleDF in pdDFs.items():
        if len(singleDF.index) > 0 and ixDF is None:
            # ixDF = singleDF.copy(deep=True)# unnecessary as default is a deep copy.
            ixDF = singleDF.copy()
            dropCols = []
            for col in singleDF.columns:
                dropCols.append(col)
            ixDF.drop(dropCols, axis=1, inplace=True)
        ixDF, alignedDF = ixDF.align(singleDF, join='outer')
        alignedDFs[chanName] = alignedDF
        ixDF.drop(ixDF.columns, axis=1, inplace=True)
    fullyAligned = {}
    for chanName, singleDF in alignedDFs.items():
        if "GSH-3" in chanName:
            i = -10
        if not len(singleDF.index) == len(ixDF.index):
            tempDF, typedDF = ixDF.align(singleDF, join='outer')
            dropCols = [col for col in typedDF.columns if not col in pdDFs[chanName].columns]
            typedDF = typedDF.drop(dropCols, axis=1)
        else:
            typedDF = singleDF
        typedDF = fillDF(typedDF)
        fullyAligned[chanName] = typedDF
    return ixDF, fullyAligned

def mergeDaskDFs(daskDFs):
    # daskDFs = alignDaskDFs(daskDFs)
    df = None
    for chanName, singleDF in daskDFs.items():
        ## unnecessary if using the alignDaskDFs method and dfs are aligned properly.
        # if len(singleDF.index) == 0 and not df is None:
        #     pass
        #     for col in list(singleDF.columns):
        #         df[col] = np.nan
        # elif df is None:
        if df is None:
            df = singleDF
        else:
            df = dd.merge(df, singleDF, how='outer', left_index=True, right_index=True)
    return df

def alignDaskDFs(daskDFs):
    # note: this method is broken and does not work on dataframes with non-matching partitions.
    ixDF = None
    alignedDFs = {}
    for chanName, singleDF in daskDFs.items():
        if len(singleDF.index) > 0 and ixDF is None:
            ixDF = singleDF
            dropCols = []
            for col in singleDF.columns:
                dropCols.append(col)
            ixDF = ixDF.drop(dropCols, axis=1)

            ixDF = ixDF.repartition(npartitions=1)
        # repartitioning seems to be necessary to maintain the dataframes index and not drop inexplicably
        # note that this leads to large load times.
        ixDF = ixDF.repartition(npartitions=N_PARTITIONS)
        singleDF = singleDF.repartition(npartitions=N_PARTITIONS)
        if "GSH-3" in chanName:
            i=-10
        ixDF, alignedDF = ixDF.align(singleDF, join='outer')
        alignedDFs[chanName] = alignedDF

        ixDF = ixDF.drop(ixDF.columns, axis=1)
    fullyAligned = {}
    ixDF = ixDF.repartition(npartitions=N_PARTITIONS)
    for chanName, singleDF in alignedDFs.items():
        if "GSH-3" in chanName:
            i=-10
        typedDF = singleDF.repartition(npartitions=N_PARTITIONS)
        tempDF, typedDF  = ixDF.align(typedDF, join='outer')
        typedDF = typedDF.repartition(npartitions=N_PARTITIONS)
        dropCols = [col for col in typedDF.columns if not col in daskDFs[chanName].columns]
        typedDF = typedDF.drop(dropCols, axis=1)
        typedDF = fillDF(typedDF)
        fullyAligned[chanName] = typedDF

    return ixDF, fullyAligned

def fillDF(df):
    df = df.bfill(limit=2)
    df = df.ffill(limit=2)
    return df

def getNextArchive(archive):
    rootFolder = archive.archivePath.parent
    validArchives = []
    for folder in rootFolder.iterdir():
        try:
            if datetime.datetime.strptime(folder.name, "%Y-%m-%d_%H-%M-%S") > datetime.datetime.strptime(archive.archiveName, "%Y-%m-%d_%H-%M-%S"):
                validArchives.append(folder)
        except Exception as e:
            logging.info(f'Will not attempt to add archive {folder} to list of possible archives to process due to exception: {e}')
    nextArchiveList = sorted(validArchives, key=lambda x: datetime.datetime.strptime(x.name, "%Y-%m-%d_%H-%M-%S"))
    if nextArchiveList:
        nextArchive = nextArchiveList[0]
    else:
        nextArchive = None
    return nextArchive


def loadDF(archive, debugMode = False, wholeExperiments=False):
    # Ensure that each field in the reader records are unique by appending the controller name to it, if necessary.
    # At the same time, change the name of that column in the dataframe, if necessary.
    logging.info(f'Loading in data from archive')
    archStart = tu.nowEpoch()
    startExperimentT = None
    endExperimentT = None
    eventTimes = []
    eventFiltering=0
    dataTimes=[]
    appendingTimes = []

    # load events from all the archives. Used in filtering experiments
    tEventStart = tu.nowEpoch()
    archiveEvents = loadEvents(archive)

    # filter out only the whole experiments from the archive events.
    incompleteStartedEvents=None # events that have been started, but the corresponding "finish" event/experiment does not appear.
    incompleteFinishedEvents=None # events that have been finished, but the corresponding "start" event/experiment does not appear.
    if wholeExperiments:
        startExperimentT, endExperimentT, wholeArchiveExperiments, incompleteFinishedEvents, incompleteStartedEvents = filterWholeEvents(archiveEvents)
        archiveEvents = wholeArchiveExperiments
    eventTimes.append(tu.nowEpoch()-tEventStart)

    # load in data from archive.
    archStartTS = tu.nowEpoch()
    # archiveDF = loadArchiveDF(archive, asDask=asDask)  # a single dask dataframe of all the data in the archive.
    archiveDF = loadArchivePDDF(archive, debugMode=debugMode)

    dataTimes.append(tu.nowEpoch()-archStartTS)

    daskPost = tu.nowEpoch()
    #attempting to fill na using map partitions.
    # finalDF = archiveDF.fillna(method="bfill", limit=2)
    daskPost = tu.nowEpoch()-daskPost
    logging.info(f'Successfully loaded in data from archive'
                 f'\n\tEvent Reading: {sum(eventTimes)} seconds.'
                 f'\n\tEvent Filtering: {eventFiltering} seconds.'
                 f'\n\tData Loading: {sum(dataTimes)} seconds.'
                 f'\n\tData Appending: {sum(appendingTimes)} seconds.'
                 f'\n\tDask Post: {daskPost} seconds.'
                 f'\n\tTotal: {tu.nowEpoch() - archStart} seconds.\n')
    return startExperimentT, endExperimentT, archiveEvents, archiveDF, incompleteStartedEvents, incompleteFinishedEvents

def saveDaskDFs(ixDF, archiveDFs):
    ixPath = fileByChannelPath.joinpath("INDEX.parquet")
    ixDF = ixDF.reset_index()
    ixDF.to_parquet(ixPath, write_index=False)
    for chanName, df in archiveDFs.items():
        dfPath = fileByChannelPath.joinpath(chanName + '.parquet')
        saveDF = df.reset_index()
        saveDF.to_parquet(dfPath, write_index=False)

def loadDFsFromFiles():
    archiveDFs = {}
    ixDF = None
    for singleFile in fileByChannelPath.iterdir():
        chanName = singleFile.stem
        df = dd.read_parquet(singleFile)
        if chanName == "INDEX":
            ixDF = df.set_index('timestamp', sorted=True)
        else:
            if 'timestamp' in df.columns:
                df = df.set_index('timestamp', sorted=True)
            elif 'index' in df.columns:
                df = df.set_index('index', sorted=True)
            archiveDFs[chanName] = df
    return ixDF, archiveDFs

def cleanTempFolder():
    try:
        shutil.rmtree(tempFilePath)
    except Exception as e:
        pass

def saveArchiveDFs(archive):
    # load an archive's raw data into a dataframe.
    # todo: uncomment after debugging.
    dataChannels = {}
    for channelName, channelIO in archive.channelMap.items():
        if not isCorrected(channelName) and ChannelType.Data in channelIO.typeMap:
            try:
                allChanDFs = archive.read(channelName, channelType=ChannelType.Data, asDF=True)
                if len(allChanDFs) > 1:
                    channelDF = pd.concat(allChanDFs)
                else:
                    channelDF = allChanDFs[0]
                # added these next 2 lines to try and get around dumb "ACannot convert NA/INF to int issue.
                # if not len(channelDF.dropna(how="all").index) == 0:
                #     channelDF = channelDF.dropna(how='all')
                channelDF.dropna(how='all', axis=0, inplace=True) # drop any na rows.
                channelDF['timestamp'] = channelDF['timestamp'].astype(int)
                dropped = channelDF.drop_duplicates(subset=['timestamp'], keep="first")
                indexedDF = dropped.set_index('timestamp')

                # todo: come up with better way to dynamically change the column names based on if the field has the
                #   controller name in it or not.
                contName = channelName.split('.')[0]
                renameCols = {}
                for colName in list(indexedDF.columns):
                    if not contName in colName and not "timestamp" in colName:
                        renameCols[colName] = ".".join([contName, colName])
                renamedDF = indexedDF.rename(renameCols, axis=1)
                dataChannels[channelName] = renamedDF
            except Exception as e:
                logging.exception(e)

    # ixDF, finalDFs = alignDaskDFs(dataChannels)
    # saveDaskDFs(ixDF, finalDFs)
    # ixDF, finalDFs = alignPDDfs({name: df.compute() for name, df in dataChannels.items()})
    ixDF, finalDFs = alignPDDfs({name: df for name, df in dataChannels.items()})
    return ixDF, finalDFs

def loadArchiveDFs(archive):
    ixDF, finalDFs = saveArchiveDFs(archive)
    # ixDF, finalDFs = loadDFsFromFiles()
    return ixDF, finalDFs

def loadArchivePDDF(archive, debugMode=False):
    ixDF, archiveDFs = loadArchiveDFs(archive)
    finalDF = mergePDDfs(archiveDFs)
    return finalDF

def loadArchiveDaskDF(archive, asDask=False, debugMode=False):

    fullDFPath = unifiedCompletePath.joinpath('Complete.parquet')
    if not debugMode or not os.path.exists(fullDFPath):
        ixDF, archiveDFs = loadArchiveDFs(archive, asDask)
        dfDict = {name: df.compute() for name, df in archiveDFs.items()}
        finalDF = mergeDaskDFs(dfDict)
        finalDF.to_parquet(fullDFPath, write_index=True)
    finalDF = dd.read_parquet(fullDFPath)
    finalDF = finalDF.set_index('timestamp')
    return finalDF

def filterWholeEvents(allLoadedEvents):
    expIDs = {}
    for singleEvent in allLoadedEvents:
        # if the experiment ID exists and is not in the dictionary expIDs, add it
        if singleEvent.get('expID') and not expIDs.get(singleEvent.get('expID')):
            expIDs[singleEvent.get('expID')] = {}
        # todo: make the below 'experiment start/end' strings into event types.
        if 'Experiment Started' in singleEvent.values():
            expIDs[singleEvent.get('expID')]['started'] = singleEvent['timestamp']
        if 'Experiment Ended' in singleEvent.values():
            expIDs[singleEvent.get('expID')]['ended'] = singleEvent['timestamp']
    fullExpsByID = sorted(list(filter(lambda expID:
                             ("started" in expIDs[expID]) &
                             ("ended" in expIDs[expID]), expIDs.keys())),
                        key=lambda x: expIDs[x]['started'])
    startedExpsByID = sorted(list(filter(lambda expID:
                             ("started" in expIDs[expID]) &
                             (not (expID in fullExpsByID)), expIDs.keys())),
                        key=lambda x: expIDs[x]['started'])
    endedExpsByID = sorted(list(filter(lambda expID:
                             ("ended" in expIDs[expID]) &
                             (not (expID in fullExpsByID)), expIDs.keys())),
                        key=lambda x: expIDs[x]['ended'])
    fullExperimentEvents = list(filter(lambda x: x.get('expID') in fullExpsByID, allLoadedEvents))
    startedExperimentEvents = list(filter(lambda x: x.get('expID') in startedExpsByID, allLoadedEvents))
    endedExperimentEvents = list(filter(lambda x: x.get('expID') in endedExpsByID, allLoadedEvents))
    if fullExpsByID:
        dfStart = int(expIDs[fullExpsByID[0]]['started'])
        dfEnd = int(expIDs[fullExpsByID[-1]]['ended'])
    else:
        dfStart = None
        dfEnd = None
    # todo: what if there are adhoc events that don't have an experiment ID that happened before the experiment?
    return dfStart, dfEnd, fullExperimentEvents, startedExperimentEvents, endedExperimentEvents

def loadEvents(archive):
    guiChannel = "MainGUI"
    guiEvents = archive.read(channel=guiChannel, channelType=ChannelType.Event)
    allEvents = []
    mistakenNamedEvents = archive.read(channel='Thread-65', channelType=ChannelType.Event) # common replacement for MainGUI.
    if guiEvents:
        for eventList in guiEvents:
            for singleEvent in eventList:
                allEvents.append(singleEvent)
    if mistakenNamedEvents:
        for eventList in mistakenNamedEvents:
            for singleEvent in eventList:
                allEvents.append(singleEvent)
    return allEvents


def loadWeather(weatherPath):
    finalDF = pd.DataFrame()
    try: # attempt first to parse based on METEC characteristics.
        logging.info(f'Attempting to parse MET data using METEC format.')
        metecDF = pd.read_csv(weatherPath)

        def toEpoch(dtStr):
            dt = tu.strToDT(dtStr, format=tu.formats[tu.FormatKeys.ExcelCSV])
            epoch = tu.DTtoEpoch(dt)
            return epoch

        dt = metecDF['Date Time']
        epoch = dt.apply(lambda x: toEpoch(x)).astype(int)
        temp = metecDF[' Ch004(C)'].astype(float)
        rh = metecDF[' Ch006(%)'].astype(float)
        ws = metecDF['Ch001(M/S)'].astype(float)
        wDir = metecDF[' Ch003(Deg)'].astype(float)
        press = metecDF[' Ch007(mbar)'].astype(float)

        finalDF['timestamp'] = epoch
        finalDF['WindSpeed(m/s)'] = ws
        finalDF['WindDir(degN)'] = wDir
        finalDF['RelativeHumidity(percent)'] = rh
        finalDF['Temperature(C)'] = temp
        finalDF['Pressure(mBar)'] = press

        return finalDF
    except Exception as e:
        logging.error(f'Could not parse Weather data using METEC format.'
                      f'\n\terror: {e}')# data is in form of Christman data.
    try:# get MET data from Christman using their format
        logging.info(f'Attempting to use Christman format.')
        chDF = pd.read_csv(weatherPath)
        chDF.drop(chDF.index[0], inplace=True)  # drop the units
        finalDF = pd.DataFrame()
        # epoch = chDF['timestamp'].astype(int)
        epochFloat = pd.to_numeric(chDF['timestamp'], errors='coerce')
        epoch = epochFloat.astype(int)
        temp = chDF['Temp'].astype(float)
        rh = chDF['RH'].astype(float)
        ws = chDF['Wind'].astype(float)  # in M/S
        wDir = chDF['Dir'].astype(float)
        press = chDF['Press'].astype(float)

        finalDF['timestamp'] = epoch
        finalDF['WindSpeed(m/s)'] = ws
        finalDF['WindDir(degN)'] = wDir
        finalDF['RelativeHumidity(percent)'] = rh
        finalDF['Temperature(C)'] = temp
        finalDF['Pressure(mBar)'] = press
        return finalDF
    except Exception as e:
        logging.error(f'Could not parse Weather data using Christman format.')
    return finalDF


ARGS_METADATA = {
    'description': 'Post Processing',
    'args': [
        {'name_or_flags': ['-a', '--archive'],
         'default': None,
         'help': 'Path to the archive to be analyzed'},
        {'name_or_flags': ['-g', '--GC'],
         'default': None,
         'help': 'Path to the gas composition history file.'},
        {'name_or_flags': ['-r', '--RManifest'],
         'default': None,
         'help': 'Path to the readers csv where slope/offset and other metadata regarding the device can be found.'},
        {'name_or_flags': ['-p', '--EPManifest'],
         'default': None,
         'help': 'Path to the file where the historic emission point records are stored.'},
        {'name_or_flags': ['-m', '--FMManifest'],
         'default': None,
         'help': 'Path to the file where the historic emission point records are stored.'},
        {'name_or_flags': ['-w', '--weather'],
         'default': None,
         'help': 'Path to file where timestamped met data from either METEC or Christman is stored..'},
        {'name_or_flags': ['-s', '--minSettlingTime'],
         'default': 60,
         'help': 'Minimum settling time for events.'}
    ]
}

def addTimestamps(records):
    for i in range(0, len(list(records.keys()))):
        startTS = sorted(list(records.keys()))[i]
        endTS = sorted(list(records.keys()))[i+1] if i+1 < len(records.keys()) else tu.MAX_EPOCH
        records[startTS]['startEpoch'] = startTS
        records[startTS]['endEpoch'] = endTS

def loadPostComponents(readerPath, epManifest, fmManifest, gcManifest, weather, archivePath, minSettlingTime):
    """ Load in the dataframes and manifested records from the filepaths passed in through the arguments. """
    manStart = tu.nowEpoch()
    logging.info('Loading in manifests')
    readerRecords = fUtils.loadSummary(readerPath, asDF=True)  # reads in reader records from csvs as dicts.
    addTimestamps(readerRecords)

    epRecords = fUtils.loadSummary(epManifest, asDF=True)  # reads in ep records as pandas dataframes.
    addTimestamps(epRecords)

    fmRecords = fUtils.loadSummary(fmManifest, asDF=True) # reads in flowmeter records as a pandas dataframe.
    addTimestamps(fmRecords)

    try:
        gcRecords = fUtils.loadSummary(gcManifest, asDF=True) # reads in gc records as pandas dataframes.
        addTimestamps(gcRecords)
    except:
        gcRecords = GCSummary(gcManifest)

    # NOTE: loading in weather still needs to be implemented
    externalWeatherData = loadWeather(weather) # reads in weather data from either christman or metec 1 minute averaged data.

    archive = daFromArchive(pathlib.Path(archivePath))
    logging.info(f'Successfully loaded manifests. '
                 f'\n\tTotal seconds: {tu.nowEpoch() - manStart}\n')

    return readerRecords, epRecords, fmRecords, gcRecords, externalWeatherData, archive, int(minSettlingTime)