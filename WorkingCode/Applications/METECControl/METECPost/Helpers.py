import logging
from functools import wraps

import pandas as pd
import dask.dataframe as dd
import dask.diagnostics as diag
import time

from Utils import TimeUtils as tu

class RecordError(Exception): pass

def resourceWrapped(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        with diag.Profiler() as rProf:
            results = method(*args, **kwargs)
            time.sleep(1)
            rProf.visualize()
            return results
    return wrapper

def correctReaderRecords(readerRecords, dataframe):
    for record in readerRecords.values():
        loadedRecord = record['LoadedRecord']
        record['fieldRename'] = {}
        for readerName, fields in loadedRecord.items():
            ctrlr = fields['Controller']
            record['fieldRename'][readerName] = {}
            for fieldName, fieldMD in fields['fields'].items():
                record['fieldRename'][readerName][fieldName] = fieldName
                if not ctrlr in fieldName:
                    # using controller name if it is guaranteed to be unique, or the reader name if it isn't.
                    ctrlrConflict = list(
                        filter(lambda x: ctrlr == loadedRecord[x]["Controller"], loadedRecord.keys()))
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
                if field in dataframe.columns:
                    dataframe.rename(columns={field:fields[field]}, inplace=True)

def customConcat(d1, d2, asDask=False):
    # doing len(index) instead of df.empty because empty is expensive in dask
    try: # if both dataframes are not empty, join
        # a1, b1 = d1.align(d2, join="outer", axis=1) # commented out because it wasn't working todo: figure out
        # final = dd.concat([a1, b1])
        # todo: figure out how to eliminate duplicate rows based on duplicate indices.
        # inxBools = ~pd.Series(final.index.values.compute(), index=final.index.values.compute()).duplicated(keep='first')
        if asDask:
            final = dd.concat([d1, d2])
        else:
            final = pd.concat([d1, d2])
        return final
    except Exception as e: # One or more dataframe is empty, return the other, or second df if both are empty.
        raise e
    if not len(d1.index)==0:
        return d1
    return d2

def isBetween(val, start, end):
    if start <= val and val <= end:
        return True
    return False

def addSubPeriods(subPeriods, key, records):
    # note: the first time this is called on subPeriods, subPeriods should be a single entry of {'startEpoch': 0, 'endEpoch': [nowEpoch]}

    for recordTime, singleRecord in records.items():
        # this for loop handles the case that the record starts within the start and end times of the period.
        persStarting = list(filter(
            lambda x:
            x['startEpoch'] < singleRecord['startEpoch'] and singleRecord['startEpoch'] < x['endEpoch'],
            subPeriods))
        for singlePeriod in persStarting:
            firstPeriod = {
                **singlePeriod,
                'startEpoch': singlePeriod['startEpoch'],
                'endEpoch': singleRecord['startEpoch'],
                key: singlePeriod.get(key, None)
            }
            secondPeriod = {
                **singlePeriod,
                'startEpoch': singleRecord['startEpoch'],
                'endEpoch': singlePeriod['endEpoch'],
                key: singleRecord}
            subPeriods.remove(singlePeriod)
            subPeriods.append(firstPeriod)
            subPeriods.append(secondPeriod)

        # these lines handle the case that the record ends within the span of the periods.
        endPeriods = list(
            filter(lambda x: x['startEpoch'] < singleRecord['endEpoch'] and singleRecord['endEpoch'] < x['endEpoch'],
                   subPeriods))
        for singlePeriod in endPeriods:
            firstPeriod = {
                **singlePeriod,
                'endEpoch': singleRecord['endEpoch'],
                key: singleRecord
            }
            secondPeriod = {
                **singlePeriod,
                'startEpoch': singleRecord['endEpoch'],
                key: singlePeriod.get(key, None)}
            subPeriods.remove(singlePeriod)
            subPeriods.append(firstPeriod)
            subPeriods.append(secondPeriod)

    for singlePeriod in subPeriods:
        # this handles the case that the record spans a period (starts before a period starts and ends after the period ends.
        recordsSpanning = list(filter(
            lambda x:
            x['startEpoch'] <= singlePeriod['startEpoch'] and singlePeriod['endEpoch'] <= x['endEpoch'], # case that the record spans in this period.
            records.values()))
        for singleRecord in recordsSpanning:
            singlePeriod[key] = singleRecord

# todo: use the reader record mapping associated with the controller at the proper time.
def readerNameFromCtrlr(ctrlr, readerRecords):
    corrReader = list(filter(lambda x: readerRecords[x]['Controller'] == ctrlr, readerRecords.keys()))
    if len(corrReader) > 1:
        i=-10
    return corrReader[0]
    # if ctrlr:
    #     ctrlrLong = ctrlr.split('.')[0]
    #     rdr = '.'.join([ctrlrLong, 'LJ-1'])
    #     return rdr
    # return None

# @resourceWrapped
def findMinMaxTS(rawDFs):
    ix = rawDFs.index
    startTS = ix[0]
    endTS = ix[-1]
    return startTS, endTS

def ctrlrNameFromReader(reader, readerRecords):
    ctrlr = None
    if reader:
        ctrlr = readerRecords.get(reader,{}).get('Controller')
    return ctrlr

def getCorrespRecord(startTS, endTS, recordManifest):
    corrRecord = list(filter(lambda x: x['startEpoch'] <= startTS and endTS <= x['endEpoch'], recordManifest))
    if len(corrRecord) == 0:
        raise RecordError(f'No Records found in timestamp range:'
                              f'\n\tstart time {tu.EpochtoDT(startTS)} (UTC)'
                              f'\n\tend time {tu.EpochtoDT(endTS)} (UTC)')
    elif len(corrRecord) > 1:
        raise RecordError(f'Multiple Records found in timestamp range:'
                                  f'\n\tstart time {tu.EpochtoDT(startTS)} (UTC)'
                                  f'\n\tend time {tu.EpochtoDT(endTS)} (UTC)')
    return corrRecord[0]

def processSingleRecord(reader, subDF, corrFM, corrEP, corrReader, calibrations, startTS, endTS):

    # todo: these lines works for 'regular' control boxes, but does not work for things like the GMR. Figure out a way to do that for GMR without hard coding it in.
    rMD = corrReader[reader]['fields']
    # output valves for controller boxes.
    flowValves = {valveName: md for valveName, md in rMD.items() if
                  md.get('flow_type') == 'flow'}  # for determining output states
    outputValves = {valveName: md for valveName, md in rMD.items() if
                    md.get('flow_type') == 'output'}  # for determining EP in combo with epRecord
    fvrc = {}  # flow valve nested dictionary by row/col/state during the event.
    # todo: how to get calibration curve?
    if not subDF.empty:
        ctrlr = ctrlrNameFromReader(reader, corrReader)
        fmRow = corrFM.where(corrFM.Controller == ctrlr)
        fmIndex = fmRow.Controller[fmRow.Controller == ctrlr].index
        fm = fmRow['Flowmeter ID'][fmIndex]
        avgFlow = float(subDF[fm].mean().iloc[0])
        for valveName, valveMD in flowValves.items():
            r = valveMD['row']
            c = valveMD['col']
            if not r in fvrc.keys():
                fvrc[r] = {}
            val = subDF[valveName].iloc[0]
            if not pd.isna(val):
                fvrc[r][c] = val
        rowsEmitting = {}
        for row, colInfo in fvrc.items():
            rowsEmitting[row] = {'emitting': False,
                                 'colStates': ''}
            colKeys = sorted(colInfo.keys())
            for col in colKeys:
                colState = colInfo[col]
                if colState == 0: # 0 means pulled down, and therefore emitting.
                    rowsEmitting[row]['emitting'] = True
                rowsEmitting[row]['colStates'] = ''.join([rowsEmitting[row]['colStates'], str(int(colState))])
        eps = []
        for valveName, valveMD in outputValves.items():
            r = valveMD['row']
            c = valveMD['col']
            rowEmitting = rowsEmitting[r]['emitting']
            if rowEmitting:
                outputState = int(subDF[valveName].iloc[0])
                ab = "A" if outputState == 1 else "B"
                corrEP['ctrlr'] = pd.DataFrame({'CB': ['CB-']* len(corrEP.Pad)}).CB
                corrEP['ctrlr'] = corrEP['ctrlr'].str.cat(corrEP.Pad.astype(str))
                corrEP['ctrlr'] = corrEP['ctrlr'].str.cat(corrEP.Controller.astype(str))
                epRow = corrEP.where((corrEP.ctrlr == ctrlr) &
                                     (corrEP.Active == 1) &
                                     (corrEP['Valve Row'] == r) &
                                     (corrEP['Valve Position'] == ab)).dropna(how='all')
                ep = epRow['Emission Point'].iloc[0]
                eps.append(ep)

        event = {'startTS': startTS, 'endTS': endTS, 'reader': reader, 'avgFlow': avgFlow, 'emissionPoints': eps}
        return event
    i = -10

def processEvents(df, flags, epRecords, readerRecords, fmRecords):
    readerEvents = {}
    for reader, allRows in flags.items():
        controllerEvents = []
        for rowNum, timestamps in allRows.items():
            controllerEvents = [*controllerEvents, *timestamps]
        sortedEvents = list(sorted(set(controllerEvents)))
        readerEvents[reader] = sortedEvents

    calibrations = {}
    stableEmissions = {}
    startupEmissions = {}
    # todo: do this next part per controller, not per reader. This will allow things link the GMR to work better.
    for reader, tsList in readerEvents.items():
        for i in range(0, len(tsList)-1):
            eventStart = tsList[i]
            eventEnd = tsList[i+1]
            try:
                # eventEnd is really the timestamp of the start of the next event.
                subDF = df.where((eventStart <= df.timestamp) & (df.timestamp < eventEnd)).dropna(how='all')
                corrFM = getCorrespRecord(eventStart, eventEnd, fmRecords)['record']
                corrEP = getCorrespRecord(eventStart, eventEnd, epRecords)['record']
                corrReader = getCorrespRecord(eventStart, eventEnd, readerRecords)['record']
                event = processSingleRecord(reader, subDF, corrFM, corrEP, corrReader, calibrations, eventStart, eventEnd)
                # found all the events!! Now need to bin them, and apply the calibration curves.
            except RecordError as e:
                logging.error(e)
    return {}

def getEpField(epRow, ep, fieldName):
    try:
        return epRow[fieldName].iloc[0]
    except:
        return None

def isManifoldValve(fieldName, fieldMD):
    keys = fieldMD.keys()
    if 'EV' in fieldName and 'row' in keys and 'col' in keys and 'flow_type' in keys:
        return True
    return False

def isFlowmeter(fieldName, fieldMD):
    if "FM" in fieldName:
        return True
    return False

def isFlowSetpoint(fieldName, fieldMD):
    if 'MASS_FLOW_SETPOINT' in fieldName:
        return True
    return False

def isTruckFlowmeter(flowmeterName):
    if "TRK" in flowmeterName:
        return True
    return False

def isGMRFlowmeter(flowmeterName):
    if "GMR" in flowmeterName:
        return True
    return False

def isGSHFlowmeter(flowmeterName):
    if "GSH" in flowmeterName:
        return True
    return False