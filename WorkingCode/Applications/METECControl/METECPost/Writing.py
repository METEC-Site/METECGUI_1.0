import csv
import logging
import os
import shutil

import pandas as pd

from Applications.METECControl.METECPost import Helpers as hp
from Applications.METECControl.METECPost.ControlledRelease import ControlledRelease
from Utils import TimeUtils as tu

def writeAllData(metarecords, outputFolder):
    metDF = writeMetData(metarecords, outputFolder)
    manifoldDF = writeManifoldData(metarecords, outputFolder)
    miscDF = writeMiscData(metarecords, outputFolder)
    flowDF = writeFlowData(metarecords, outputFolder)
    return flowDF, manifoldDF, metDF, miscDF

# def writeRawData(metarecords, outputFolder, readerRecords):
#     flowPath = os.path.join(outputFolder, f'SensorReadings1hz.csv')
#     if os.path.exists(flowPath):
#         os.remove(flowPath)
#     for metarecord in metarecords:
#         placeholderDF = metarecord.rawDask
#         if not os.path.isfile(flowPath):
#             placeholderDF.to_csv(flowPath, single_file=True, index=False)
#         else:
#             placeholderDF.to_csv(flowPath, mode='a', header=False, single_file=True, index=False)

def writeMetData(metarecords, outputFolder):
    dfs = []
    for mr in metarecords:
        dfs.append(mr.getMetData())
    finalDF = writeData(dfs, outputFolder, 'MET1hz.csv')
    return finalDF

def writeManifoldData(metarecords, outputFolder):
    dfs = []
    for mr in metarecords:
        dfs.append(mr.getManifoldData())
    finalDF = writeData(dfs, outputFolder, 'Manifold1hz.csv')
    return finalDF

def writeMiscData(metarecords, outputFolder):
    dfs = []
    for mr in metarecords:
        dfs.append(mr.getMiscData())
    finalDF = writeData(dfs, outputFolder, 'Misc1hz.csv')
    return finalDF

def writeFlowData(metarecords, outputFolder):
    dfs = []
    for mr in metarecords:
        dfs.append(mr.getFlowData())
    finalDF = writeData(dfs, outputFolder, 'SensorReadings1hz.csv')
    return finalDF

def writeData(dataFrames, outputFolder, fileName):
    dfPath = os.path.join(outputFolder, fileName)
    if os.path.exists(dfPath):
        os.remove(dfPath)
    finalDF = None
    for df in dataFrames:
        if finalDF is None:
            finalDF = df
        else:
            pd.concat([finalDF, df])
    if not os.path.isfile(dfPath) and not finalDF is None:
        finalDF.to_csv(dfPath, index=True)
    return finalDF

def copyNotes(outputFolder):
    notesInput = os.path.join(os.path.abspath(os.path.dirname(__file__)), "Notes on Fields - For Operators.docx")
    notesOutput = os.path.join(outputFolder, "Notes on Fields.docx")
    if not os.path.exists(notesOutput):
        shutil.copy(notesInput, notesOutput)

def writeControlledReleases(allEvents, outputFolder):
    eventPath = os.path.join(outputFolder, f'ControlledReleases.csv')
    if len(allEvents) > 0:
        logging.info(f'Writing Events to output path {eventPath}')
        with open(eventPath, 'w', newline='') as ePath:
            fieldNames = ControlledRelease.fields
            writer = csv.DictWriter(ePath, fieldNames)
            writer.writeheader()
            for event in allEvents:
                row = event.getAllFields()
                writer.writerow(row)
        logging.info(f'Finished writing events to output path.')
    else:
        logging.info(f'No events found to write to output path {eventPath}')
    return pd.read_csv(eventPath)

def writeOutputDataframe(dataframe, readerRecords, path):
    tStart = tu.nowEpoch()
    logging.info(f'Writing raw results to output path {path}')
    pd.DataFrame(data=[dataframe.columns]).to_csv(path, header=False, index=False)  # write the header/column names
    units = {col: '' for col in dataframe.columns}
    try:
        # get latest metadata. #todo: get the proper metadata associated with this record.
        mdRecord = readerRecords[-1]['record']
        for channelName, channelMD in mdRecord.items():
            for fieldName, fieldInfo in channelMD['fields'].items():
                joinedName = '.'.join([channelName, fieldName])
                outputUnits = fieldInfo.get('output_units', '')
                if joinedName in dataframe.columns:
                    units[joinedName] = outputUnits
                elif fieldName in dataframe.columns:
                    units[fieldName] = outputUnits
    except:
        mdRecord = {}
    dataframe.rename(columns=units).to_csv(path, mode='a', index=False)  # writing the data.
    logging.info(f'Finished writing timeseries to output path: {path}. '
                 f'Elapsed Time: {tu.nowEpoch()-tStart}')

def getReadyForSaving(dataframe, readerRecords):
    dt = dataframe.timestamp.apply(lambda x: tu.EpochtoDT(x).strftime('%Y-%m-%d_%H:%M:%S'))
    renameColumns(dataframe, readerRecords)
    dataframe.insert(0, "Datetime-UTC", dt)
    tsCol = dataframe.timestamp
    dataframe.drop('timestamp', axis=1, inplace=True)
    dataframe.insert(0, "timestamp", tsCol)

def renameColumns(dataframe, readerRecords):
    # todo: get the correct record associated with this timestamp, not just the latest one.
    colNames = {c: c for c in dataframe.columns}
    corrRec = list(readerRecords.values())[-1]['LoadedRecord']
    for readerName, readerInfo in corrRec.items():
        controller = readerInfo['Controller']
        for singleField in readerInfo['fields'].keys():
            if singleField in colNames and not controller in singleField:
                colNames[singleField] = '.'.join([controller, singleField])
    dataframe.rename(columns=colNames, inplace=True)
    dataframe.sort_index(axis=1, inplace=True)