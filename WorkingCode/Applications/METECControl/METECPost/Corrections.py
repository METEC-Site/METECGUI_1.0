import logging
import re
from functools import reduce

import pandas as pd
from Utils import Conversion as conv
from Utils import TimeUtils as tu

# A list of all fields that, if they contain the following regex string, should be treated as a field with that controls the states of flow.
STATE_CHANGE_FIELDS = [
    re.compile("MFC_MASS_FLOW_SETPOINT"),
    re.compile("EV-[0-9]*")
]

# A list of all fields that, if they contain the following regex string, should be treated as a field with flow property information.
FLOW_PROPERTY_FIELDS = [
    re.compile('GAS_NUMBER'),
    re.compile('MFC_MASS_FLOW'),
    re.compile('MFC_PRESSURE'),
    re.compile('MFC_FLOW_TEMPERATURE'),
    re.compile('MFC_VOLUMETRIC_FLOW'),
    re.compile('MFC_MASS_FLOW'),
    re.compile("PT-[0-9]*"),
    re.compile("TC-[0-9]*"),
    re.compile("FM-[0-9]*")
]

# A list of all fields that, if they contain the following regex string, should be treated as misc.
MISC_PROPERTY_FIELDS = [
    re.compile('COMMAND_ID'),
    re.compile('COMMAND_STATUS'),
    re.compile('DEVICE_STATUS_LEAST'),
    re.compile('DEVICE_STATUS_MOST')
]

MET_PROPERTY_FIELDS = [
    re.compile('AT'),
    re.compile('ST'),
    re.compile('RH'),
    re.compile('WS'),
    re.compile('WD'),
    re.compile('WE'),
    re.compile('UWS'),
    re.compile('VWS'),
    re.compile('WWS'),
    re.compile('GND'),
    re.compile('BP'),
    re.compile('BV')
]

def applyReaderCorrections(subDF, readerRecord, gcRecord):
    corrDF = subDF # currently subDF is an uncalculated Dask Dataframe.
    cols = corrDF.columns
    for readerName in readerRecord.keys():
        unfoundFields = []
        fields = readerRecord[readerName]['fields']
        # todo: come up with a better way to correct the keys/fields of this dictionary.
        for fieldName in list(fields.keys()):
            ctrlName = readerName.split('.')[0]
            if not readerName.split('.')[0] in fieldName:
                f = fields.pop(fieldName)
                fields['.'.join([ctrlName, fieldName])] = f

        for field in fields.keys():
            if field in cols:
                try:
                    if 'MET-' in field or "MET-" in readerName:
                        gndColName = list(filter(lambda x: 'GND' in x, fields.keys()))[0]
                        gndColumn = subDF[gndColName]
                        if not "GND" in field: # don't correct the ground column.
                            corrDF[field] = metDataCorrection(subDF[field], readerName, gndColumn, readerRecord)
                    elif ('GSH' in field and "FM" in field):
                        corrCol = slopeOffset(subDF[field], readerName, readerRecord)
                        col = gcKFact(corrCol, gcRecord, kFact="KLambdaAvg")
                        corrDF[field] = col
                    elif ("TRK" in field and "FC" in field):
                        corrCol = slopeOffset(subDF[field], readerName, readerRecord)
                        col = gcKFact(corrCol, gcRecord, kFact="KEtaAvg")
                        corrDF[field] = col
                    else:
                        corrCol = slopeOffset(subDF[field], readerName, readerRecord)
                        fieldProps = readerRecord[readerName]['fields'][field]
                        outputUnits = fieldProps.get("output_units")
                        if outputUnits == "F":
                            corrCol = corrCol.apply(lambda val: conv.convert(val, 'F', "C"))
                        elif outputUnits == 'PSIA':
                            corrCol = corrCol.apply(lambda val: conv.convert(val, 'PSIA', "kPa"))
                        corrDF[field] = corrCol
                except KeyError as e:
                    unfoundFields.append(field)
                except Exception as e:
                    logging.error(f'Error when attempting to correct field {field}: {e}')
        if unfoundFields:
            logging.info(f'Unable to correct fields for reader {readerName}, check that the record loaded correctly:'
                         f'\n\t{unfoundFields}')
    return corrDF

def gcKFact(column, record, kFact):
    name = column.name
    corrGSH = re.search('GSH-[1-9]', name)
    if corrGSH:
        corrGSH = corrGSH[0]
    else:
        return column
    gshRow = record.loc[record['gas_house']==corrGSH]
    if len(gshRow.index) == 1: # 1:1 match with gas house and its record
        gshRecord = gshRow.iloc[0]
        kFact = gshRecord[kFact]
        return column*float(kFact)
    elif len(gshRow.index) == 0:
        # no matching gas house record found.
        logging.info(f'No GC records found. Cannot correct flowmeter {name}')
        return column
    else:
        # multiple gas house records found.
        logging.info('Multiple GC records found. Cannot correct flowmeter {name}')
        return column


def slopeOffset(column, readerName, record):
    name = column.name
    readerRecord = record.get(readerName, {})
    fields = readerRecord.get('fields', {})
    columnRecord = fields.get(name, {})
    slope = columnRecord.get('slope',None)
    offset = columnRecord.get('offset',None)


    if not slope is None and not offset is None:
        # return column*float(slope)+float(offset)
        return column*slope+offset
    else:
        return column

def metDataCorrection(column, readerName, gndColumn, record):
    if not column.name == 'timestamp':
        correctedColumn = column-gndColumn
        correctedColumn.name = column.name
        return slopeOffset(correctedColumn, readerName, record)
    else:
        return column

def normalizeReaderRecordNames(readerRecords):
    # note: flagging the fields to be renamed if the controller isn't in the fieldname, and then prepending the controller
    # name (if that will be unique) or the reader name (if prepending controller name won't be unique).
    for record in readerRecords.values():
        loadedRecord = record['LoadedRecord']
        record['fieldRename'] = {}
        for readerName, fields in loadedRecord.items():
            ctrlr =  fields['Controller']
            record['fieldRename'][readerName] = {}
            for fieldName, fieldMD in fields['fields'].items():
                record['fieldRename'][readerName][fieldName] = fieldName
                if not ctrlr in fieldName:
                    # using controller name if it is guaranteed to be unique, or the reader name if it isn't.
                    ctrlrConflict = list(filter(lambda x: ctrlr == loadedRecord[x]["Controller"], loadedRecord.keys()))
                    ctrlrConflict = set(filter(lambda x: fieldName in loadedRecord[x]['fields'], ctrlrConflict))
                    if len(ctrlrConflict) > 1:
                        record['fieldRename'][readerName][fieldName] = '.'.join([readerName, fieldName])
                    else:
                        record['fieldRename'][readerName][fieldName] = '.'.join([ctrlr, fieldName])
        # rename the fields in the reader to match what it should be to be unique.
        for readerName, fields in record['fieldRename'].items():
            for field in list(fields.keys()):
                rec = loadedRecord[readerName]['fields'].pop(field)
                loadedRecord[readerName]['fields'][fields[field]] = rec


def renameReaderFields(dataframe, readerRecord, channelName):
    """Rename the fields in the dataframe from the original to the new updated field based on the fieldRename mapping."""
    fieldRename = readerRecord['fieldRename']
    readerRename = fieldRename[channelName]
    dataframe.rename(columns=readerRename, inplace=True)
    return dataframe

def dropEmptyChannels(dataFrames):
    dropDFChannels = []
    for channelName, df in dataFrames.items():
        if df.empty:
            dropDFChannels.append(channelName)
    for channelName in dropDFChannels:
        dataFrames.pop(channelName)

def removeSources(dataFrames):
    for channelName, dataFrame in dataFrames.items():
        if 'source' in dataFrame.columns:
            dataFrame.drop('source', inplace=True, axis=1)

def rectifyTimestamps(dataFrames):
    timestampsDFs = {k: pd.DataFrame({"timestamp":v['timestamp']}) for k, v in dataFrames.items()}
    timestampDF = reduce(lambda left, right: pd.merge(left, right, on=['timestamp'], how='outer', sort=True), list(timestampsDFs.values()))
    timestampDF['timestamp'] = timestampDF['timestamp'].astype(int)
    timestampDF.drop_duplicates(keep='first', inplace=True)
    for channelName, df in dataFrames.items():
        df['timestamp'] = df['timestamp'].astype(int)
        df.drop_duplicates(keep='first', inplace=True)
        mergedDF = pd.merge(timestampDF, df, on=['timestamp'], how='outer', sort=True)
        mergedDF.fillna(inplace=True, axis=0, limit=2, method='backfill')
        dataFrames[channelName] = mergedDF
    return dataFrames

def mergeDaskDataframes(dfDict, compress=True):
    """ A method to merge dataframes on timestamp as index, with a backfill (limit to 2). Returns one singular dataframe with all the values."""
    mergeStart = tu.nowEpoch()
    logging.info(f'Starting merge on dataframe.')
    # dropEmptyChannels(dfDict)
    tsCorrected = rectifyTimestamps(dfDict)
    # following lines are the old way of doing this compression. High memory usage.
    if compress:
        for dfName, df in dfDict.items():
            compressDataframe(df)
    finalDF = None
    for ts in list(tsCorrected.keys()):
        df = tsCorrected.pop(ts)
        if finalDF is None:
            finalDF = df
        else:
            tempDF = pd.merge(finalDF, df, on=['timestamp'], how='outer', sort=True)
            del finalDF
            finalDF=tempDF
            del tempDF
            del df
    logging.info(f'Successfully merged dataframe.'
                 f'\n\tTotal seconds: {tu.nowEpoch() - mergeStart}\n')
    return finalDF

def compressDataframe(metecDF):
    "Downcast all columns with the following tags to an integer instead of float column."
    compressIf = ["EV", "COMMAND_STATUS", "COMMAND_ID", "GAS_NUMBER"]
    toInts = set()
    for col in metecDF.columns:
        for singleCompressionKey in compressIf:
            if singleCompressionKey in col:
                toInts.add(col)
                # pd.to_numeric(metecDF[col], errors="coerce", downcast='integer')
    for col in toInts:
        metecDF[col] = pd.to_numeric(metecDF[col], downcast='integer', errors='coerce')

def isFlowProperty(fieldName):
    for searchPattern in FLOW_PROPERTY_FIELDS:
        if re.search(searchPattern, fieldName):
            return True
    return False

def isMiscProperty(fieldName):
    for searchPattern in MISC_PROPERTY_FIELDS:
        if re.search(searchPattern, fieldName):
            return True
    return False


def isMetProperty(fieldName):
    for searchPattern in MET_PROPERTY_FIELDS:
        if re.search(searchPattern, fieldName):
            return True
    return False


def isStateProperty(fieldName):
    for searchPattern in STATE_CHANGE_FIELDS:
        if re.search(searchPattern, fieldName):
            return True
    return False

def splitPandasDataframes(readerCorrectedDataframe):

    flowColumns = list(filter(lambda x: isFlowProperty(x) or 'timestamp' in x, readerCorrectedDataframe.columns))

    rdrStateColumns = list(filter(lambda x: isStateProperty(x) or 'timestamp' in x, readerCorrectedDataframe.columns))
    rdrMiscColumns = list(filter(lambda x: isMiscProperty(x) or 'timestamp' in x, readerCorrectedDataframe.columns))
    metColumns = list(filter(lambda x: isMetProperty(x) or 'timestamp' in x or "MET" in x, readerCorrectedDataframe.columns))
    readerFlowDF = readerCorrectedDataframe.filter(flowColumns)
    rdrMiscDF = readerCorrectedDataframe.filter(rdrMiscColumns)
    rdrStateDF = readerCorrectedDataframe.filter(rdrStateColumns)
    metDF = readerCorrectedDataframe.filter(metColumns)

    del readerCorrectedDataframe
    return readerFlowDF, rdrMiscDF, rdrStateDF, metDF

def normalizeHeader(channelName, fieldName):
    return '.'.join([channelName, fieldName])