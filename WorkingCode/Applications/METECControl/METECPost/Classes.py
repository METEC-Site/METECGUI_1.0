import logging
import math
import re

import numpy as np
import pandas as pd
from Applications.METECControl.METECPost import Helpers as hp
from Applications.METECControl.METECPost.ControlledRelease import ControlledRelease
from Applications.METECControl.METECPost.Corrections import applyReaderCorrections
from Applications.METECControl.METECPost.QC import QC_FLAGS, getBaseQC, addQCFlag, toDigit
from Framework.BaseClasses.Events import EventTypes
from Utils import Conversion as conv
from Utils import TimeUtils as tu

pd.options.mode.chained_assignment = None # prevents annoying error codes from popping up when assigning columns in DFs.


class RecordError(Exception): pass

class StateMatchError(Exception): pass

class CalExistsError(Exception): pass

# todo: would be nice to have a cal ID for each cal period. That way it is explicit which cals happened when.
# before 5 sec, an event is considered 'transitioning'
# after 5 sec and before 10 sec, the event is 'settling'
# after 10 sec, the event is 'settled'
TRANSITION_TIME = 3 # seconds #todo: make this the minimum time between events from the same flowmeter if using automated testing.
BEST_ESTIMATE_THRESHOLD = 20 # 20 seconds minimum to use event's own flowrate as a best estimate.
# MIN_SETTLING_TIME = 120 # used in old versions of the code to determine settling time. Now is passed in as command line argument.

def MRFactory(dataframe, readerRecords, epRecords, fmRecords, gcRecords, allLoadedEvents, minSettlingTime):
    """A method that separates dataframes and manifests of records into their sub periods of metarecords."""
    MetaRecord.setClassEvents(allLoadedEvents)
    allMRs = []

    # streamlined way of computing index. Now uses client computation to unload memory burden.
    ix = dataframe.index
    startTS = tu.MIN_EPOCH
    endTS = tu.MAX_EPOCH
    if len(ix) > 0:
        startTS = ix[0]
        endTS = ix[-1]

    # previous way of computing min/max timestamp of the dask.
    # tsComp = daskClient.submit(hp.findMinMaxTS, rawDask)
    # startTS, endTS = tsComp.result()

    subPeriod =  {
        'startEpoch': startTS,
        'endEpoch': endTS,
    }
    allPeriods = [subPeriod]
    hp.addSubPeriods(allPeriods, 'readerRecord', readerRecords)
    hp.addSubPeriods(allPeriods, 'epRecord', epRecords)
    hp.addSubPeriods(allPeriods, 'fmRecord', fmRecords)
    hp.addSubPeriods(allPeriods, 'gcRecord', gcRecords)

    for singlePeriod in allPeriods:
        startTS = singlePeriod.get('startEpoch')
        endTS = singlePeriod.get('endEpoch')
        rr = singlePeriod.get('readerRecord')
        ep = singlePeriod.get('epRecord')
        fm = singlePeriod.get('fmRecord')
        gcs = singlePeriod.get('gcRecord')
        periodDask = dataframe.loc[lambda df: (startTS <= df.index) & (df.index <= endTS)]


        try:
            MR = MetaRecord(startTS, endTS, periodDask, rr, ep, fm, gcs, minSettlingTime)
            allMRs.append(MR)
        except RecordError as e:
            logging.error(f'Could not create Metarecord for following period due to exception: '
                          f'\n\tPeriod Start: {tu.EpochtoDT(float(startTS))} UTC'
                          f'\n\tPeriod End: {tu.EpochtoDT(float(endTS))} UTC'
                          f'\n\tError: {e}')
    return allMRs


class MetaRecord():
    EventID = 1
    referenceRecords = []
    allEmissions = []
    importedExperimentEvents = []
    importedCalEvents = []
    importedEmissionEvents = []
    importedExperimentsByID = {}
    allLoadedEvents = []

    """ Holds all necessary records for a single time period (start epoch to end epoch) for
    that time period. Only records that are pertinent for that time period are passed as single instances into this
    class, so all records can be used on the subDF without needing to check for a timestamp compatibility.
    """

    def __init__(self, startTS, endTS, dataframe,  readerRecord, epRecord, fmRecord, gcRecord, minSettlingTime):
        self.tsStart = int(startTS)
        self.utcStart = tu.EpochtoDT(int(startTS))
        self.tsEnd = int(endTS)
        self.utcEnd = tu.EpochtoDT(int(endTS))
        self.minSettlingTime = minSettlingTime
        # self.corrDask = applyReaderCorrections(rawDask, readerRecord)
        # self.daskInx = self.rawDask.index.compute() # here to see if indexing will speed up accessing.
        self.readerRecord = readerRecord['LoadedRecord']
        self.epRecord = epRecord['LoadedRecord'].dropna(how="all", axis=0)
        self.gcRecord = gcRecord['LoadedRecord']
        self.fmRecord = fmRecord['LoadedRecord']
        if not 'Row' in self.fmRecord.columns:
            self.fmRecord['Row'] = None
        self.rawDataframe = dataframe
        self.corrDataframe = None

        self.automatedEventFlags = {}
        self.referenceEmissions = {}
        self.loneEmissions = {}
        self.allEmissionEvents = {}
        self._findExpEvents() # putting reference events inside the importedExperimentsByID dictionary.
        self._filterEmissionEvents()
        self.valveChangeFlags = {}
        self.fieldsToFlag = {}
        self.fieldStates = {}
        self.knownFlowmeterMap = {}
        self.findFieldsToFlag()
        self.thisRecordEmissions = [] # todo: see if moving this to the class attribute fixes the issue where emissions don't cross between mr instances.

    def correctDataframe(self, rawDF):
        corrDF = applyReaderCorrections(rawDF, self.readerRecord, self.gcRecord)
        return corrDF
        # filePath = unifiedCompletePath.joinpath(f'{self.tsStart}-{self.tsEnd}_Corrected.csv')
        # if not unifiedCompletePath.exists():
        #     os.makedirs(unifiedCompletePath)
        # corrDF.to_csv(filePath)
        # del corrDF
        # corrDask = dd.read_csv(filePath).set_index("timestamp")
        # return corrDask

    def _runCorrection(self):
        if self.corrDataframe is None:
            # self.corrDask = self.correctRawDask(self.rawDask)
            self.corrDataframe = self.correctDataframe(self.rawDataframe)

    def getManifoldData(self):
        self._runCorrection()
        manifoldCols = ["EV"]
        return self.corrDataframe[lambda df: self._filterColumns(df, manifoldCols)]

    def getMetData(self):
        self._runCorrection()
        metCols = ["MET-"]
        return self.corrDataframe[lambda df: self._filterColumns(df, metCols)]

    def getFlowData(self):
        self._runCorrection()
        flowCols = ["TC", "PT", "FM", "FC"]
        return self.corrDataframe[lambda df: self._filterColumns(df, flowCols)]

    def getMiscData(self):
        self._runCorrection()
        miscCols = ["TC", "PT", "FM", "FC", "EV", "MET"]
        return self.corrDataframe[lambda df: self._filterColumns(df, miscCols)]

    def _filterColumns(self, df, tags):
        filteredCols = []
        for col in df.columns:
            for tag in tags:
                if tag in col:
                    filteredCols.append(col)
        return filteredCols

    @classmethod
    def setClassEvents(cls, allLoadedEvents):
        cls.importedExperimentEvents = list(
            filter(lambda x: x['eventType'] in [EventTypes.ExperimentStart, EventTypes.ExperimentEnd], allLoadedEvents))
        cls.importedCalEvents = list(
            filter(lambda x: x['eventType'] in [EventTypes.CalStart, EventTypes.CalEnd], allLoadedEvents))
        cls.importedEmissionEvents = list(filter(lambda x: x['eventType'] in [EventTypes.Emission], allLoadedEvents))
        cls.importedExperimentsByID = cls._filterByExpID(cls.importedExperimentEvents)
        cls.allLoadedEvents = allLoadedEvents

    @classmethod
    def reinitializeClassVariables(cls):
        cls.EventID = 1
        cls.referenceRecords = []
        cls.allEmissions = []
        cls.importedExperimentEvents = []
        cls.importedCalEvents = []
        cls.importedEmissionEvents = []
        cls.importedExperimentsByID = {}
        cls.allLoadedEvents = []

    @classmethod
    def _filterByExpID(cls, experimentEvents):
        expIDs = set()
        experiments = {}
        for expEvent in experimentEvents:
            expIDs.add(expEvent['expID'])
        for expID in expIDs:
            startExp = {}
            endExp = {}
            startExps = list(filter(lambda x: x['expID'] == expID and x["eventType"] == EventTypes.ExperimentStart, experimentEvents))
            if len(startExps) == 1:
                startExp = startExps[0]
            endExps = list(filter(lambda x: x['expID'] == expID and x["eventType"] == EventTypes.ExperimentEnd, experimentEvents))
            if len(endExps) == 1:
                endExp = endExps[0]
            experiments[expID] = {"start":startExp, "end": endExp}
        return experiments

    def getReaderRecord(self, fieldName):
        record = None
        corrReader = list(filter(lambda x: fieldName in self.readerRecord[x]['fields'].keys(), self.readerRecord.keys()))
        if corrReader:
            record = self.readerRecord[corrReader[0]]['fields'][fieldName]
        return record

    def findFieldsToFlag(self):
        # loop through a second time to make those headers unique.
        # this is the same correction and method done on the dataframe when loaded in from a file.
        for readerName, readerMD in self.readerRecord.items():
            readerFields = readerMD['fields']
            controller = readerMD['Controller']
            for fieldName, fieldMD in readerFields.items():
                if hp.isFlowSetpoint(fieldName, fieldMD) or hp.isManifoldValve(fieldName, fieldMD):
                    self.fieldsToFlag[fieldName] = {**fieldMD}
                    self.fieldsToFlag[fieldName]['Controller'] = controller
                    if not fieldName in self.fieldStates:
                        self.fieldStates[fieldName] = {
                            'fieldName': fieldName,
                            'eventStartTS': self.tsStart,
                            'state': None,
                            'eventEndTS': None}

    def flagExperimentZeros(self):
        for expID, expInfo in self.importedExperimentsByID.items():
            if len(expInfo['events']) > 0:
                zeroEmissions = list(filter(lambda x: x.get('FlowLevel', None) == 0, expInfo['events']))
                if len(expInfo['events']) == zeroEmissions:
                    if expInfo.get('start', {}).get('timestamp'):
                        fm = self.fmFromFieldname(zeroEmissions[0])
                        # this way of getting fm is veeery hack-ey. todo: Fix it!
                        fm = self.fmFromFieldname(".".join([zeroEmissions[0]['Controller'], list(zeroEmissions[0]['SetStates'].keys())[0]]))
                        self.valveChangeFlags[fm].append(expInfo['start']['timestamp'])
                    if expInfo.get('end', {}).get('timestamp'):
                        fm = self.fmFromFieldname(zeroEmissions[0])
                        # fm = self.fmFromFieldname(
                        #     ".".join([zeroEmissions[0]['Controller'], list(zeroEmissions[0]['SetStates'].keys())[0]]))
                        self.valveChangeFlags[fm].append(expInfo['end']['timestamp'])


    # @hp.resourceWrapped
    def flagValveTransitions(self):
        logging.info(f'Finding all valve events. ')
        s = tu.nowEpoch()

        # initialize all flowmeters to have flags at the start/end time of this record.
        for readerName, readerRecord in sorted(self.readerRecord.items(), key=lambda x: x[0]):
            for fieldName, fieldProps in sorted(readerRecord['fields'].items(), key=lambda x: x[0]):
                if hp.isFlowmeter(fieldName, fieldProps):
                    self.valveChangeFlags[fieldName] = [self.tsStart, self.tsEnd]
                elif hp.isFlowSetpoint(fieldName, fieldProps):
                    fm = self.fmFromFieldname(fieldName)
                    self.valveChangeFlags[fm] = [self.tsStart, self.tsEnd]

        # remove fields to flag if they aren't in the dataframe.
        for singleKey in list(self.fieldsToFlag.keys()):
            rdr = self.getReaderRecord(singleKey)['reader']
            dask = self.rawDataframe
            if dask is None or not singleKey in dask.columns:
                self.fieldsToFlag.pop(singleKey)

        # filter all flag keys by controller, making dataframes smaller down the line.
        flagKeys = list(self.fieldsToFlag.keys())
        fieldsByReader = {}
        for flagKey in flagKeys:
            rdr = self.getReaderRecord(flagKey)['reader']
            curFields = fieldsByReader.get(rdr)
            if curFields is None:
                curFields = set()
            curFields.add(flagKey)
            fieldsByReader[rdr] = curFields

        # iterate by controller to find the changes for each field. This is the meat and potatoes of this method.
        for reader, ctrlrKeys in fieldsByReader.items():
            self._flagChangesQuick(ctrlrKeys)

        for flowmeter, timestamps in self.valveChangeFlags.items():
            self.valveChangeFlags[flowmeter] = list(sorted(set(timestamps)))
        logging.info(f'Finished flagging valve changes.'
                     f'\n\tElapsed time: {tu.nowEpoch() - s} seconds\n\n')
        return self.valveChangeFlags

    def _flagColumnChanges(self, dfColumn):
        """ raises a flag to the self.flags dictionary under the reader name/[row or reader name] nested dict if the state changed.

        dfRow: a row of a dataframe with the timestamped record of the state of ALL valves, flowmeters, sensors, etc. in
        the site. This flag is raised if the state of any valve changed from the state in the previous row.
        """
        fieldName = dfColumn.name


        dfColumn = dfColumn.dropna(how="all")
        intCol = dfColumn.astype(int)
        shifted = pd.concat([intCol[1:], intCol[-2:-1]])
        if len(intCol) > 1: # more than one entry, do the xor analysis
            shifted.index = intCol.index
            xor = intCol ^ shifted
            final = pd.concat([xor[-2:-1], xor[0:-1]])
            final.index = intCol.index
            reduced = (final.where(lambda x: x > 0).dropna()).index.to_list()
        else:
            reduced = intCol.index.to_list()
        for timestamp in reduced:
            # todo: streamline this and reduce the overhead.
            thisEvent = {
                # 'changeTS': fieldState['eventStartTS'],
                'changeTS': int(timestamp),
                "reader": None,
                "fieldName": fieldName,
                'fieldInfo': {**self.fieldsToFlag[fieldName]}
            }
            self.addToEventFlags(thisEvent)

    def _flagChangesQuick(self, flagKeys):
        slicedDF = self.rawDataframe[[*flagKeys]]
        # dd.compute(slicedDF.loc[lambda df: (self.tsStart <= df.index) & (df.index < self.tsEnd)].compute().apply(lambda col: self._flagColumnChanges(col), axis=0)) # old dask way of doing things.
        slicedDF.loc[lambda df: (self.tsStart <= df.index) & (df.index < self.tsEnd)].apply(lambda col: self._flagColumnChanges(col), axis=0)


    # # @hp.resourceWrapped
    # def _flagChanges(self, flagKeys):
    #     # slice the Dataframe by each field needed to flag.
    #     try:
    #         slicedDF = self.rawDask[[*flagKeys]]
    #         slicedDF = slicedDF.loc[lambda df: (self.tsStart <= df.index) & (df.index < self.tsEnd)]
    #         slicedDF = slicedDF.compute()
    #
    #         # apply the slicing method to the dataframe columns.
    #         slicedDF.apply(lambda col: self._flagColumnChanges(col), axis=0)
    #         # slicedDF.apply(lambda row: self._flagRowChanges(row, flagKeys), axis=1)
    #         del slicedDF
    #     except Exception as e:
    #         raise Exception(e) # here for debugging

    def _flagSingleValChange(self, fieldName, curState, timestamp):
        fieldState = self.fieldStates[fieldName]
        prevState = fieldState['state']
        flagged = False
        if not np.isnan(curState) and (not (curState == prevState)):
            flagged = True

        if flagged:
            thisEvent = {
                # 'changeTS': fieldState['eventStartTS'],
                'changeTS': int(timestamp),
                "reader": None,
                "fieldName": fieldName,
                'fieldInfo': {**self.fieldsToFlag[fieldName]}
            }
            self.addToEventFlags(thisEvent)
            fieldState['eventStartTS'] = int(timestamp)
            fieldState['state'] = float(curState)
        else:
            # simply increment the timer while keeping the start time and state the same.
            fieldState['eventEndTS'] = int(timestamp)


    def _flagRowChanges(self, dfRow, fieldNames, offVal=1):
        """ raises a flag to the self.flags dictionary under the reader name/[row or reader name] nested dict if the state changed.

        dfRow: a row of a dataframe with the timestamped record of the state of ALL valves, flowmeters, sensors, etc. in
        the site. This flag is raised if the state of any valve changed from the state in the previous row.
        """
        inx = dfRow.name
        for name in fieldNames:
            self._flagSingleValChange(name, dfRow[name], inx)


    def _sortTimestamps(self, eventTimestamps):
        """ Sorts the event timestamps passed from a specific flowmeter into a dictionary of the following type:

        {
        "tStart": start time of event, indicating when the first valve was opened
        "tTransitioned": time when the last valve remained closed/opened after a certain threshold.
        "tSettled": initially set to the tEnd.
        "tEnd": time at which these valves are changed and the next event begins.
        }
        """
        sortedTimestamps = []
        if len(eventTimestamps) == 0:
            return sortedTimestamps
        if len(eventTimestamps) == 1:
            t = eventTimestamps[0]
            sortedTimestamps.append({'tStart':t, 'tTransitioned': t, 'tEnd':t})
        tStart = tTranstion = eventTimestamps[0]
        for i in range(0, len(eventTimestamps)):
            thisT = eventTimestamps[i]
            if (thisT - tTranstion) <= TRANSITION_TIME:
                # number of seconds since the last transition (starting at tStart) is less than the allowed transition time.
                tTranstion = thisT
            else:
                # add a new entry, since the end of this event has been reached.
                newEntry = {'tStart': tStart, 'tTransitioned': tTranstion, 'tEnd': thisT}
                sortedTimestamps.append(newEntry)

                try:
                    # reset timestamps, so the start of a new event is the end of this event.
                    tStart = tTranstion = eventTimestamps[i]
                except:
                    pass
        return sortedTimestamps

    def processFlags(self):
        """ Process all the flags associated with all flowmeters across the site. """
        allTSFM = []
        for flowmeterName, eventTimestamps in self.valveChangeFlags.items():
            # list of dictionaries of format {"tStart":, "tTransitioned":, "tSettled":, "tEnd":}
            eventTimestamps = self._sortTimestamps(eventTimestamps)
            for singleTimstampRecord in eventTimestamps:
                allTSFM.append((singleTimstampRecord, flowmeterName))
        sortedTSFM = sorted(allTSFM, key=lambda x: (x[0]['tStart'], x[1]))# sort by timestamp first, then by flowmeter name.

        logging.info(f'Processing flags for record {self.tsStart} - {self.tsEnd}')
        newStart = tu.nowEpoch()
        for tsRecord in sortedTSFM:
            self.processSingleRecord(tsRecord[0], tsRecord[1])
        logging.info(f'Finished processing flags.'
                     f'\n\tElapsed time: {tu.nowEpoch() - newStart} seconds\n\n')

        # old way of processing records. Compute called many times.
        # oldStart = tu.nowEpoch()
        # for singleTimstampRecord, flowmeterName in sortedTSFM:
        #     recordDF = self.rawDask.loc[(singleTimstampRecord["tStart"] <= self.rawDask.index) & (self.rawDask.index <= singleTimstampRecord["tEnd"])].compute()
        #     events = self.processSingleRecord(recordDF, singleTimstampRecord, flowmeterName)
        #     if events:
        #         for event in events:
        #             self.thisRecordEmissions.append(event)
        #             self.allEmissions.append(event)
        #         MetaRecord.EventID += 1
        # logging.info(f'Finished parsing events the old way.'
        #              f'\n\tElapsed time: {tu.nowEpoch() - oldStart} seconds\n\n')

        # old way of processing records. Compute called many times.
        # for singleTimstampRecord, flowmeterName in sortedTSFM:
        #     events = self.processSingleRecord(singleTimstampRecord, flowmeterName)
        #     if events:
        #         for event in events:
        #             self.thisRecordEmissions.append(event)
        #             self.allEmissions.append(event)
        #         MetaRecord.EventID += 1


    def processSingleRecord(self, timestamps, flowmeterID):
        """ A method that will return a SINGLE event from a controller. It will be agnostic of calibration curves,
        other controller states, etc

        An event should contain the relevant states of a single emission point.

        For manifold valves, this will be: row and output state, incorportating the upstream flowmeter information
        and the downstream EP information, as well as the row information at the control box.

        For GMR information, is should contain the row(s) that the ev is open on, as well as flowrates of the gases."""
        # process as a gas house flowmeter.
        # todo: move compute here, before all the info is computed, so that it is only done once per "single record".
        tStart = timestamps['tStart']
        tEnd = timestamps['tEnd']
        tTransitioned = timestamps['tTransitioned']
        # tTransitioned is the time at which the valves have stopped fluctuating.
        #   Therefore it should be used to calculate the flows/etc on all active emission points.
        if tStart == tEnd:
            return None
        fmReader = self.getReaderRecord(flowmeterID)['reader']
        # eventDF = self.rawDataframe.loc[lambda df: (tTransitioned <= df.index) & (df.index <= tEnd)].compute()
        eventDF = self.rawDataframe.loc[lambda df: (tTransitioned <= df.index) & (df.index <= tEnd)]
        if flowmeterID in eventDF.columns:
            flowmeterDF = eventDF[flowmeterID] # todo: pick up here, what about if the flowmeter is missing?
        else:
            flowmeterDF = None

        tSettled, throwMissingFlag = self.calculateSettlingTime(flowmeterDF, tTransitioned, tEnd, flowmeterID) # find the settling time for this event.

        if hp.isGMRFlowmeter(flowmeterName=flowmeterID):
            # todo: grabbing the flow data from the gas mixing rig.
            cbsDownstreamFM = self.controllersFromFM("GMR-1")
            # allEPs = self._getGMREps(cbsDownstreamFM)
            # activeEPs = self._filterActiveEPsGMR(flowmeterDF, tTransitioned, tEnd, allEPs)
            # activeEPCount = len(activeEPs) # todo: fill this in with a correct calculation.
            activeEPCount=0
            activeEPs = None
            gcRecord = {}
        elif hp.isTruckFlowmeter(flowmeterName=flowmeterID):
            # todo: obtain average lambda and k factor from overall GC records.
            gcRecord = {}
            activeEPCount = 1
            activeEPs = self._getTruckEPs()
        elif hp.isGSHFlowmeter(flowmeterName=flowmeterID):
            cbsDownstreamFM = self.controllersFromFM(flowmeterID)
            allControllerEPs = self._getAllEPs(cbsDownstreamFM)
            activeEPs = self._filterActiveEPs(eventDF, tTransitioned, tEnd, allControllerEPs)
            gcRecord = self._getGCInfo(flowmeterID)
            activeEPCount = len(activeEPs)
        else:
            raise NameError(f"Flowmeter {flowmeterID} is not a recognized flowmeter type.")

        # todo: get the experiment ID from 'events' generated within framework.
        experimentID = None

        allEvents = []
        baseEvent = ControlledRelease()
        baseEvent.setExperimentInfo(eventID=MetaRecord.EventID, ExperimentID=experimentID, QCFlags=getBaseQC(),
                                tStart=tStart, tTransitioned=tTransitioned, tSettled=tSettled, tEnd=tEnd,
                                FlowmeterID = flowmeterID, ActiveEPCount=activeEPCount)
        if throwMissingFlag:
            addQCFlag(QC_FLAGS.SETTLED_MISSING, baseEvent)

        for fieldName, fieldValue in gcRecord.items():
            baseEvent.addField(fieldName, fieldValue)
        if activeEPs:
            for ep in activeEPs:
                epEvent = ControlledRelease(**baseEvent.getAllFields())
                epEvent.setEmissionPointInfo(**ep.getEmissionPointInfo())
                allEvents.append(epEvent)
        else:
            allEvents.append(baseEvent)

        for event in allEvents:
            if hp.isGMRFlowmeter(flowmeterName=flowmeterID):
                # todo: grabbing the flow data from the gas mixing rig.
                self._calcGMRFlow(eventDF, event)
            elif hp.isTruckFlowmeter(flowmeterName=flowmeterID):
                # todo: obtain average lambda and k factor from overall GC records.
                self._calcTruckFlow(eventDF, event)
            elif hp.isGSHFlowmeter(flowmeterName=flowmeterID):
                self._calcGSHFlow(eventDF, event)
            else:
                raise NameError(f"Flowmeter {flowmeterID} is not a recognized flowmeter type.")
        if allEvents:
            for event in allEvents:
                self.thisRecordEmissions.append(event)
                self.allEmissions.append(event)
            MetaRecord.EventID += 1
        return allEvents

    def _compileFullRecord(self, event, gcRecord, allEPs=None):
        allEvents = []

        if not allEPs:
            allEPs = []
        for singleEP in allEPs:
            newEvent = ControlledRelease(**event.getAllFields())
            newEvent.setEmissionPointInfo(**singleEP)
            newEvent.setGCInfo(**gcRecord)
            allEvents.append(newEvent)
        return allEvents

    def _getGCInfo(self, flowmeter):
        ignoreFields = ['StartDate', 'StartTime', 'EndDate', 'EndTime', 'gas_house', 'cylinder', 'analysis_type',
                        'raw_record_path', 'serial_number', 'isoDate'] # GCSampleCount is the run number
        # GC Calculations # todo: make sure this is per gas house/flowmeter!
        gcSourceRecord = list(filter(lambda x: flowmeter in x[1]['fields'].keys(), self.readerRecord.items()))
        gcSourceName = gcSourceRecord[0][1]['Controller']
        gcRecord = {}
        houseRecord = self.gcRecord.loc[self.gcRecord['gas_house'] == gcSourceName]
        for column in houseRecord.columns:
            if not column in ignoreFields:
                gcRecord[column] = houseRecord[column].iloc[0]
        return gcRecord

    def _getTruckEPs(self):
        # todo: implement this
        return None

    def _getGMREps(self, cbsDownstreamFM):
        allEPRows = []
        for cb in cbsDownstreamFM:
            thisCBRow = self.epRecord.where(self.epRecord["CB"] == cb).dropna(how="all", axis=0)
            for row in thisCBRow.iterrows():
                allEPRows.append({"controllerName": cb, "dfRow": row})
        return allEPRows

    def _getAllEPs(self, controllerNames):
        allEPs = list()
        for controllerName, controllerRow in controllerNames:
            try:
                controllerEPs = self.findCurrentEPs(controllerName, controllerRow)
                for singleEP in controllerEPs:
                    allEPs.append(singleEP)
            except Exception as e:
                logging.error(e)
        return allEPs

    def _getGMRreader(self):
        return ['GMR-1.FC-1', 'GMR-1.FC-2', 'GMR-1.FC-3', 'GMR-1.FC-4']

    def _filterActiveEPsGMR(self, eventDF, tTransitioned, tEnd, allEPs):
        # iterate through ALL gmr readers for this EP.
        activeEPs = []
        rdrs = self._getGMRreader()
        ctrl = allEPs[0]['controllerName']
        epRow = allEPs[0]['dfRow'][1]
        t3RowNumbers, t3FlowValves, t3OutputValves, t3Thermocouples, t3PressureTransducers = self._findSensorsByController("CB-3T")
        ljRowNumbers, ljFlowValves, ljOutputValves, ljThermocouples, ljPressureTransducers = self._findSensorsByController("GMR-1.LJ-1")
        for rdr in rdrs:
            rowNumbers, gmrFlowValves, gmrOutputValves, gmrThermocouples, gmrPressureTransducers = self._findSensorsByController(rdr)
            # todo: pick up here.
            compiledEP = self.compileActiveEP(rdr, eventDF, tTransitioned, tEnd, ctrl, epRow, rowStateRep, outputValveName, outputValveInfo, thermocouples, pressureTransducers)
            activeEPs.append(compiledEP)
        return allEPs

    def _filterActiveEPs(self, eventDF, tTransitioned, tEnd, allEPs):
        activeEPs = []
        for ep in allEPs:
            ctrl = ep['controllerName']
            rowNumbers, allFlowValves, allOutputValves, thermocouples, pressureTransducers = self._findSensorsByController(
                ctrl)
            if allOutputValves:
                rdr = self.getReaderRecord(allOutputValves[0][0])['reader']
            elif allFlowValves:
                rdr = self.getReaderRecord(allFlowValves[0][0])['reader']
            elif thermocouples:
                rdr = self.getReaderRecord(thermocouples[0][0])['reader']
            elif pressureTransducers:
                rdr = self.getReaderRecord(pressureTransducers[0][0])['reader']
            else:
                rdr = ctrl + ".LJ-1"
            dfRow = ep['dfRow']
            try: # old version of EP configs
                epRow = dfRow["Valve Row"]
            except: # new version of EP configs
                epRow = dfRow["Row"]
            epFlowValves = list(filter(lambda x: x[1]['row'] == epRow, allFlowValves))
            outputValve = list(filter(lambda x: x[1]['row'] == epRow, allOutputValves))
            emittingValves = []
            for valveName, valveInfo in epFlowValves:
                emittingValves.append((valveName, valveInfo))
            outputValveName, outputValveInfo = outputValve[0]
            outputvalveState = self._getOutputValveState(eventDF, tTransitioned, tEnd, outputValveName, outputValveInfo)
            rowStateRep = self._calcRowStateRep(eventDF, tTransitioned, tEnd, emittingValves)
            if rowStateRep: # rowStateRep is None if the values are na.
                try: # old version of EP configs
                    if not toDigit(rowStateRep) == 0 and dfRow["Active"] == 1 and dfRow["Valve Position"] == outputvalveState:
                        compiledEP = self.compileActiveEP(rdr, eventDF, tTransitioned, tEnd, ctrl, epRow, rowStateRep, outputValveName, outputValveInfo, thermocouples, pressureTransducers)
                        activeEPs.append(compiledEP)
                except: # new version of EP configs
                    if not toDigit(rowStateRep) == 0 and dfRow["Active"] == 1 and dfRow["EV State"] == outputvalveState:
                        compiledEP = self.compileActiveEP(rdr, eventDF, tTransitioned, tEnd, ctrl, epRow, rowStateRep, outputValveName,
                                                          outputValveInfo, thermocouples, pressureTransducers)
                        activeEPs.append(compiledEP)
        return activeEPs

    def _getOutputValveState(self, eventDF, tTransitioned, tEnd, outputValveName, outputValveInfo):
        applicableDF = eventDF[outputValveName].dropna(how='all')
        if not applicableDF.empty:
            firstState = applicableDF.iloc[0]
            if firstState == 1:
                return "A"
            elif firstState == 0:
                return "B"
            else:
                return None
        else:
            return None


    def findCurrentEPs(self, controllerName, controllerRow=None):
        eps=[]
        rowNumbers, allFlowValves, allOutputValves, thermocouples, pressureTransducers = self._findSensorsByController(controllerName)
        for valveName, valveInfo in allOutputValves:
            if (controllerRow) and (not controllerRow==valveInfo.get('row',0)) and (not np.isnan(controllerRow)):
                continue # this should take into account new configs that added rows to the FM config column.
            cb = valveName.split('.')[0].split('-')[1] # getting just the XX of "CB-XX.EQ-Y"
            pad = int(re.search('[1-9]*', cb).group(0)) if re.search('[1-9]*', cb).group(0) else None
            cont = re.search('[a-zA-Z].*', cb).group(0) if re.search('[a-zA-Z].*', cb).group(0) else None
            try: #old version of EP configs
                epRows = self.epRecord.where((self.epRecord['Pad'] == int(pad)) &
                                             (self.epRecord['Controller'] == str(cont)) &
                                             (self.epRecord["Active"] == int(1)) &
                                             (self.epRecord['Valve Row'] == int(valveInfo['row']))).dropna(how="all", axis=0)
            except Exception as e:
                epRows = self.epRecord.where((self.epRecord['Pad'] == int(pad)) &
                                             (self.epRecord['Controller'] == str(cont)) &
                                             (self.epRecord["Active"] == int(1)) &
                                             (self.epRecord['Row'] == int(valveInfo['row']))).dropna(how="all", axis=0)
            for inx, row in epRows.iterrows():
                eps.append({"controllerName": controllerName, "dfRow": row})
        return eps

    def compileActiveEP(self, rdr, eventDF, tTransitioned, tEnd, controllerName, rowNumber, rowStateRep, outputValveName, outputValveInfo, thermocouples, pressureTransducers):
        """
        Have determined that the emission point is on, now just need all the pressures/temps/etc put into place.
        """
        epEvent = ControlledRelease()

        controllerPAvg = None
        controllerPStd = None
        controllerTAvg = None
        controllerTStd = None
        # lazy way of doing this: won't work with the truck or GMR records.
        # todo: fix this so it isn't lazy.
        ctrlInfo = self.readerRecord[rdr]
        if len(pressureTransducers) == 1:
            rawPDF = eventDF[pressureTransducers[0][0]]
            rawPDF = rawPDF.loc[lambda df: (tTransitioned <= df.index) & (df.index < tEnd)]
            pField = ctrlInfo['fields'][pressureTransducers[0][0]]
            pDF = rawPDF.apply(lambda x: x*pField['slope']+pField['offset'])
            kPaDF = pDF.apply(lambda x: conv.convert(x, "PSIA", "kPa"))

            controllerPAvg = kPaDF.mean()
            controllerPStd = kPaDF.std()
        if len(thermocouples) == 1:
            tDF = eventDF[thermocouples[0][0]]
            tDF = tDF[lambda df: (tTransitioned <= df.index) & (df.index < tEnd)]
            cDF = tDF.apply(lambda x: conv.convert(x, "F", "C"))
            controllerTAvg = cDF.mean()
            controllerTStd = cDF.std()

        # ep calculations
        # outputDF = self.rawDask[outputValveName]
        # outputDF = outputDF[lambda df: (tTransitioned <= df.index) & (df.index < tEnd)].dropna(how='all')
        # outputState = outputDF.iloc[0]
        # ab = "A" if outputState == 1 else "B"
        ab = self._getOutputValveState(eventDF, tTransitioned, tEnd, outputValveName, outputValveInfo)
        self.epRecord['ctrlr'] = pd.DataFrame({'CB': ['CB-'] * len(self.epRecord.Pad)}).CB
        self.epRecord['ctrlr'] = self.epRecord['ctrlr'].str.cat(self.epRecord.fillna(0).Pad.astype(int).astype(str))
        self.epRecord['ctrlr'] = self.epRecord['ctrlr'].str.cat(self.epRecord.Controller.astype(str))

        # figuring out which column names are applicable for this EP record.
        # In the newer EP configs, "Row" and "EV State" are used. Older configs use "Valve Position" and "Valve Row"
        try:
            posID = "Valve Position"
            rowID = "Valve Row"
            self.epRecord[rowID]
            self.epRecord[posID]
        except:
            rowID = "Row"
            posID = "EV State"

        epRow = self.epRecord.where((self.epRecord.ctrlr == controllerName) &
                                    (self.epRecord.Active == 1) &
                                    (self.epRecord[rowID] == rowNumber) &
                                    (self.epRecord[posID] == ab)).dropna(how='all')
        ep = epRow['Emission Point'].iloc[0]
        desc = epRow['Description'].iloc[0]
        epLat = epRow['Lat'].iloc[0]
        epLong = epRow['Lon'].iloc[0]
        epAlt = epRow['Alt'].iloc[0]
        orificeControllerID = hp.getEpField(epRow, ep, "CB")
        epEquipmentGroup = hp.getEpField(epRow, ep, "EquipmentGroup")
        epEquipmentUnit = hp.getEpField(epRow, ep, "EquipmentUnit")

        epEvent.addField('OrificeControllerID', orificeControllerID)
        epEvent.addField("OrificeControllerPAvg", controllerPAvg)
        epEvent.addField("OrificeControllerPStd", controllerPStd)
        epEvent.addField("OrificeControllerTAvg", controllerTAvg)
        epEvent.addField("OrificeControllerTStd", controllerTStd)

        epEvent.addField('EPID', ep)
        epEvent.addField('EPEquipmentGroup', epEquipmentGroup)
        epEvent.addField('EPEquipmentUnit', epEquipmentUnit)
        epEvent.addField("EPDescription", desc)
        epEvent.addField("EPLatitude", epLat)
        epEvent.addField("EPLongitude", epLong)
        epEvent.addField("EPAltitude", epAlt)
        epEvent.addField("EPFlowLevel", toDigit(rowStateRep))
        epEvent.addField("EPFlowSetpoint", toDigit(rowStateRep)) # todo: incorporate this field for Flow Controllers.
        return epEvent

    def _calcRowStateRep(self, eventDF, tTransitioned, tEnd, emittingValves):
        emittingValves = list(sorted(emittingValves, key=lambda x: x[1]['col']))  # sort the flow valves by column.
        evNames = [ev[0] for ev in emittingValves]
        valveDF = eventDF[evNames]
        valveRow = valveDF.loc[tTransitioned]
        try:
            rowStateRep = ''.join([str(int(valveRow[rep])) for rep in valveRow.index])
        except ValueError: #row state has or is NaN
            rowStateRep = None
        return rowStateRep

    def _findSensorsByController(self, controllerName):
        # ctrlrRdr: name of the reader for that controller. Used as a key in the reader record dictionary.
        try: # todo: clean this up. Done for GMR's where controller name IS rdr name but it is very lazy and bad.
            ctrlRdr = hp.readerNameFromCtrlr(controllerName, self.readerRecord)
        except:
            ctrlRdr = controllerName
        # fields: dictionary of all of the readers associated with that reader.
        fields = self.readerRecord[ctrlRdr]['fields']

        # extract all the different types of sensor/control units from the provided fields.
        rowNumbers = set() # set of the number of rows in this controller. [1,2,3] for example.
        allFlowValves = []
        allOutputValves = []
        thermocouples = []
        pressureTransducers = []
        for fieldName, fieldInfo in fields.items():
            if 'row' in fieldInfo:
                rowNumbers.add(fieldInfo['row'])
            if fieldInfo.get('flow_type', None) == 'flow':
                allFlowValves.append((fieldName, fieldInfo))
            if fieldInfo.get('flow_type', None) == 'output':
                allOutputValves.append((fieldName, fieldInfo))
            if 'TC' in fieldName:
                # the field is a thermocouple
                thermocouples.append((fieldName, fieldInfo))
            if 'PT' in fieldName:
                # field is a pressure transducer.
                pressureTransducers.append((fieldName, fieldInfo))
            if 'MASS_FLOW_SETPOINT' in fieldName:
                allFlowValves.append((fieldName, fieldInfo))
            # signifiers for MFC's
            if "MFC_PRESSURE" in fieldName:
                pressureTransducers.append((fieldName, fieldInfo))
            if "MFC_FLOW_TEMPERATURE" in fieldName:
                thermocouples.append((fieldName, fieldInfo))
        rowNumbers = list(sorted(rowNumbers))
        return rowNumbers, allFlowValves, allOutputValves, thermocouples, pressureTransducers

    def _getSensorInfo(self, sensorName):
        for controller, allSensors in self.readerRecord.items():
            for fieldName, fieldInfo in allSensors['fields'].items():
                if fieldName in sensorName:
                    return fieldInfo

    def calculateSettlingTime(self, fmDF, tTransitioned, tEnd, flowmeterName, nConsec=30):
        """ Simplified version of calculating settling time. """
        dfExists = True
        try:
            if fmDF.empty:
                dfExists = False
        except Exception as e:
            if not fmDF:
                dfExists = False
        if not dfExists:
            return tTransitioned, True # If the dataframe doesn't exist, throw the missing flag.
        fmDF = fmDF.loc[tTransitioned:tEnd]
        # ix = fmDF.index.compute()
        ix = fmDF.index
        numRows = len(ix)
        if numRows > self.minSettlingTime:
            # return ix[self.minSettlingTime+1], False #threw an error?
            return ix[self.minSettlingTime], False
        del fmDF
        return tTransitioned, True

        """ Old version of calculating settling time
        tSettled: default time of the time at which the event is settled (IE the flow has reached minimal delta).

        f(x-Δx) - f(x+Δx) ~ 1% of full span of flowmeter for nConsecutive intervals (seconds)
        """

        # fmProps = self.getReaderRecord(flowmeterName)
        # fmSpan = fmProps['max'] if fmProps else 10 # get the max if it is there, otherwise assume 10
        # deltaThreshold = fmSpan/500 # assume settled when it is 1% of the max in variation.
        # if numRows < nConsec:
        #     tSettled = tTransitioned
        # else:
        #     settledTime = [tTransitioned] # need these variables to be mutable to use them in 'apply'
        #     fmDF.apply(lambda x: self._settledCDiffStdMethod(fmDF, x, flowmeterName, deltaThreshold, nConsec, settledTime), axis=1)
        #     # fmDF.apply(lambda x: self._settledStdMethod(fmDF, x, flowmeter, deltaThreshold, nConsec, settledTime),
        #                # axis=1)
        #     tSettled = settledTime[0]
        # return tSettled # returning tSettled simply returns the default, which at this time is tStart.

    def _settledStdMethod(self, overallDF, dfRow, flowmeterName, threshold, nConsec, settledTime):
        if not settledTime[0] is None: # if have found the settled time, then don't bother with calculations (to speed things up)
            return
        inx = dfRow.name
        firstInx = overallDF.first_valid_index()
        lastInx = overallDF.last_valid_index()
        if inx-int(nConsec/2) < firstInx or inx+int(nConsec/2) > lastInx:
            return
        frameLowerInx = inx - int(nConsec / 2)
        frameUpperInx = inx + int(nConsec / 2)
        stDev = overallDF[flowmeterName].iloc[frameLowerInx:frameUpperInx].std()
        if stDev < threshold:
            settledTime[0] = dfRow['timestamp']
        return

    def _settledCDiffStdMethod(self, overallDF, dfRow, flowmeterName, threshold, nConsec, settledTime):
        if not settledTime[0] is None: # if have found the settled time, then don't bother with calculations (to speed things up)
            return
        inx = dfRow.name
        firstInx = overallDF.first_valid_index()
        lastInx = overallDF.last_valid_index()
        if inx-1 < firstInx or inx+1 > lastInx:
            return
        prevInx = inx - 1
        nextInx = inx + 1
        diff = self._derivative(overallDF['timestamp'][prevInx], overallDF[flowmeterName][prevInx], overallDF['timestamp'][nextInx], overallDF[flowmeterName][nextInx])
        if not abs(diff) < threshold:
            return
        frameUpperLimit = inx+nConsec if inx+nConsec < lastInx else lastInx
        if frameUpperLimit - inx < nConsec/2:
            return
        stDev = overallDF[flowmeterName][inx:frameUpperLimit].std()
        if stDev < threshold:
            settledTime[0] = dfRow['timestamp']
        return

    def _derivative(self, x1, fx1, x2, fx2):
        return (fx2-fx1)/(x2-x1)

    def addToEventFlags(self, thisEvent):
        fieldName = thisEvent['fieldName']
        flowmeter = self.fmFromFieldname(fieldName)

        if not flowmeter in self.valveChangeFlags:
            self.valveChangeFlags[flowmeter] = []
        if not thisEvent['changeTS'] == None:
            self.valveChangeFlags[flowmeter].append(thisEvent['changeTS'])

    def fmFromFieldname(self, fieldName):
        # following 3 lines are to try to help speed up accessing here.
        fmID = self.knownFlowmeterMap.get(fieldName, None)
        if fmID:
            return fmID
        reader = list(filter(lambda x: fieldName in self.readerRecord[x]['fields'], self.readerRecord.keys()))[0]
        controller = self.readerRecord[reader]["Controller"]
        try:
            # this is appropriate for manifold valves
            fmIdx = self.fmRecord.where(self.fmRecord.Controller == controller).dropna(how='all').index
            fmID = self.fmRecord['Flowmeter ID'].iloc[fmIdx].iloc[0]
        except:
            # this is appropriate for Alicat Flow Controllers
            fmID = list(filter(lambda x: "MASS_FLOW" in x and not "SETPOINT" in x, self.readerRecord[reader]['fields'].keys()))[0]
        self.knownFlowmeterMap[fieldName] = fmID # save this for the future.
        return fmID

    def controllersFromFM(self, flowmeter):
        ctrlRows = self.fmRecord.where(self.fmRecord['Flowmeter ID'] == flowmeter).dropna(how='all')
        ctrlrs = ctrlRows['Controller']
        rows = ctrlRows['Row']

        return list(zip(list(ctrlrs), list(rows)))

    def applyQC(self):
        """Applies calibration record to all the events in the dataframe.

        A calibration is an event that is a single emission from a flowmeter (IE flow is only routed through one
        place, so that point with that configuration of valves has that specified flowrate.)

        """
        start = tu.nowEpoch()
        logging.info(f'Applying QC for record in period: '
                     f'\n\tStart Time: {self.utcStart} UTC'
                     f'\n\tEnd Time: {self.utcEnd} UTC')
        for event in self.thisRecordEmissions:
            self._qcFlowBounds(event)
            self._applyCalCtrlT(event)
            self._applyCalCtrlP(event)

        logging.info(f'Finished applying QC.'
                     f'\n\tElapsed time: {tu.nowEpoch() - start} seconds\n\n')

    def linkExpIDs(self):
        for singleEmission in self.thisRecordEmissions:
            startTime = singleEmission.tStart
            endTime = singleEmission.tEnd
            numEmissions = singleEmission.ActiveEPCount
            # retrieve all experiment ids that had their start/end before/after this emission start.
            experimentsAtStart = list(filter(lambda x: self.importedExperimentsByID[x].get('start',{}).get('timestamp', tu.MAX_EPOCH) <= (startTime+2) # adding one to include events on the cusp.
                                             and self.importedExperimentsByID[x].get('end',{}).get('timestamp', tu.MIN_EPOCH) >= (startTime+2),
                                      self.importedExperimentsByID))
            # retrieve all experiment ids that had their start/end before/after this emission end.
            experimentsAtEnd = list(filter(lambda x: self.importedExperimentsByID[x].get('start',{}).get('timestamp', tu.MAX_EPOCH) <= (endTime-2)
                                             and self.importedExperimentsByID[x].get('end',{}).get('timestamp', tu.MIN_EPOCH) >= (endTime-2),self.importedExperimentsByID))
            # all experiments that had the start OR end of the emission within its bounds.
            allOverlappingExps = set([*experimentsAtStart, *experimentsAtEnd])
            epFlowmeter = singleEmission.FlowmeterID

            expsMatchingFMs = []
            # find the experiment that has the flowmeter from the source/GSH matching the flowmeterID in the emission.
            for exp in allOverlappingExps:
                try:
                    expInfo = self.importedExperimentsByID[exp]
                    gshNum = expInfo['start']['gasHouse']
                    if not type(gshNum) is list:
                        gshNum = [gshNum]
                    allExpFlowmeters = []
                    for singleNum in gshNum:
                        gshFlowmeters = list(set(self.fmRecord.where(lambda df: (df['GSH'] == singleNum))['Flowmeter ID'].dropna()))
                        allExpFlowmeters = list(set([*allExpFlowmeters, *gshFlowmeters]))
                    if epFlowmeter in allExpFlowmeters:
                        #once the flowmeter match is found, add it to emission and stop searching.
                        expsMatchingFMs.append(exp)
                except Exception as e:
                    logging.error(f'Could not parse gas house/source from experiment {exp} due to: {e}')

            # try to find one experiment that starts before the EP start point and ends after the ep end point
            singleOverlappingExp = list(filter(lambda x: self.importedExperimentsByID[x]['start']['timestamp'] <=singleEmission.tStart and
                                                            singleEmission.tEnd <= self.importedExperimentsByID[x]['end']['timestamp'], expsMatchingFMs))
            if len(singleOverlappingExp) == 1:
                singleEmission.addField("ExperimentID", singleOverlappingExp[0])

            # if no such experiment exists, but one experiment with matching source is found, mark it as the experiment but flag a partial.
            elif len(expsMatchingFMs) == 1 and numEmissions > 0:
                singleEmission.addField("ExperimentID", expsMatchingFMs[0])
                addQCFlag(QC_FLAGS.PARTIAL_EXP, singleEmission)
            # if multiple experiments with matching fm's overlap this event, flag multiple experiments and do not put a match.
            elif len(expsMatchingFMs) >1 and numEmissions > 0:
                addQCFlag(QC_FLAGS.PARTIAL_EXP, singleEmission)

    def linkIntents(self):
        for singleEmission in self.allEmissions:
            le = self._getLinkedEvent(singleEmission)
            isEqual = False
            if not le is None and not singleEmission is None:
                try:
                    isEqual = int(le.get("expID")) == int(singleEmission.ExperimentID)
                except:
                    isEqual = le.get("expID") == singleEmission.ExperimentID
            if le and le.get("expID") and singleEmission.ExperimentID and isEqual:
                singleEmission.addField("EmissionIntent", le.get('Intent'))
                singleEmission.addField('EmissionCategory', le.get('EmissionCategory', ""))

    def integrateRefs(self):
        for singleEmission in self.allEmissions:
            if self._isRefEmission(singleEmission):
                self.addRefEmission(singleEmission)
            elif singleEmission.ActiveEPCount == 1 and singleEmission.Duration >= BEST_ESTIMATE_THRESHOLD:
                self.addLoneEmission(singleEmission)

    def linkRefs(self):
        for singleEmission in self.thisRecordEmissions:
            try:
                if singleEmission.ActiveEPCount >0:
                    i=-10 # here for debugging
                calEvent = self._getRefEvent(singleEmission)
                calSettled = calEvent.getField('FlowAvg')
                calUnc = calEvent.getField('FlowUncertainty')
                calEventID = calEvent.getField('EventID')
                singleEmission.addField('RefEventID', calEventID)
                singleEmission.addField('RefFlowAvg', calSettled)
                singleEmission.addField('RefFlowUncertainty', calUnc)
            except CalExistsError:
                singleEmission.addField('RefEventID', None)
                singleEmission.addField('RefFlowAvg', None)
                singleEmission.addField('RefFlowUncertainty', None)
                if singleEmission.ActiveEPCount >= 1:
                    addQCFlag(QC_FLAGS.MISSING_REF, singleEmission)

    def applyEstimates(self):
            for singleEmission in self.thisRecordEmissions:
                curCount = singleEmission.ActiveEPCount
                if singleEmission.Duration > BEST_ESTIMATE_THRESHOLD and curCount == 1:
                    singleEmission.addField("BFE", singleEmission.FlowAvg)
                    singleEmission.addField("BFU", singleEmission.FlowUncertainty)
                    singleEmission.addField("BFT", "CurrentMeteredEvent")
                elif curCount == 0:
                    singleEmission.addField("BFE", 0)
                    singleEmission.addField("BFU", singleEmission.FlowAvg)
                    singleEmission.addField("BFT", "ZeroEmissionEvent")
                elif singleEmission.RefEventID:
                    singleEmission.addField("BFE", singleEmission.RefFlowAvg)
                    singleEmission.addField("BFU", singleEmission.RefFlowUncertainty)
                    singleEmission.addField("BFT", "ReferenceMeteredEvent")
                else:
                    singleEmission.addField("BFE", None)
                    singleEmission.addField("BFU", None)
                    singleEmission.addField("BFT", "IndeterminateEvent")


    def _applyCalCtrlT(self, singleEvent):
        try:
            calEvent = self._getRefEvent(singleEvent)
            tEvent = singleEvent.getField('OrificeControllerTAvg')
            tCal = calEvent.getField('OrificeControllerTAvg')
            absC = 273.15
            tRatio = (tEvent + absC) / (tCal + absC)
            singleEvent.addField('RefTRatio', tRatio)
            if tRatio > 1.1 or tRatio < .9:
                addQCFlag(QC_FLAGS.CTRLR_TEMP_DEV, singleEvent)
        except CalExistsError:
            singleEvent.addField('RefTRatio', None)
        except TypeError:
            # one or more of the necessary components is missing.
            pass

    def _applyCalCtrlP(self, singleEvent):
        try:
            calEvent = self._getRefEvent(singleEvent)
            pCal = calEvent.getField('OrificeControllerPAvg')
            pAvg = singleEvent.getField('OrificeControllerPAvg')
            absP = 0  # PSI is reported in absolute kPa already.
            pRatio = (pAvg + absP) / (pCal + absP)
            singleEvent.addField('RefPRatio', pRatio)
            if pRatio > 1.1 or pRatio < .9:
                addQCFlag(QC_FLAGS.CTRLR_PRES_DEV, singleEvent)
        except CalExistsError:
            singleEvent.addField('RefPRatio', None)
        except TypeError:
            # one or more of the necessary components is missing.
            pass

    def applyCorrectGC(self, flowmeterName, flowmeterSeries):
        if hp.isGSHFlowmeter(flowmeterName):
            gc = self._getGCInfo(flowmeterName)
            kLambda = gc['KLambdaAvg']
            return flowmeterSeries * kLambda
        elif hp.isGMRFlowmeter(flowmeterName):
            raise NotImplementedError
        elif hp.isTruckFlowmeter(flowmeterName):
            raise NotImplementedError
        raise NotImplementedError

    def _calcGMRFlow(self, eventDF, event):
        # todo: incorporate the GMR records.
        flowAvg = flowStd = delQ = c1Flow = delC1 = c2Flow = delC2  = c3Flow = delC3 = c4Flow = delC4 = thcFlow = delTHC = None

        event.addField("FlowAvg", flowAvg)
        event.addField("FlowStDev", flowStd)
        event.addField("FlowUncertainty", delQ)
        event.addField("C1FlowAvg", c1Flow)
        event.addField("C1FlowUncertainty", delC1)
        event.addField("C2FlowAvg", c2Flow)
        event.addField("C2FlowUncertainty", delC2)
        event.addField("C3FlowAvg", c3Flow)
        event.addField("C3FlowUncertainty", delC3)
        event.addField("C4FlowAvg", c4Flow)
        event.addField("C4FlowUncertainty", delC4)
        event.addField("THCFlowAvg", thcFlow)
        event.addField("THCFlowUncertainty", delTHC)

    def _calcTruckFlow(self, eventDF, event):
        # todo: incorporate the Truck records.
        flowAvg = flowStd = delQ = c1Flow = delC1 = c2Flow = delC2 = c3Flow = delC3 = c4Flow = delC4 = thcFlow = delTHC =None

        event.addField("FlowAvg", flowAvg)
        event.addField("FlowStDev", flowStd)
        event.addField("FlowUncertainty", delQ)
        event.addField("C1FlowAvg", c1Flow)
        event.addField("C1FlowUncertainty", delC1)
        event.addField("C2FlowAvg", c2Flow)
        event.addField("C2FlowUncertainty", delC2)
        event.addField("C3FlowAvg", c3Flow)
        event.addField("C3FlowUncertainty", delC3)
        event.addField("C4FlowAvg", c4Flow)
        event.addField("C4FlowUncertainty", delC4)
        event.addField("THCFlowAvg", thcFlow)
        event.addField("THCFlowUncertainty", delTHC)

    def _calcGSHFlow(self, eventDF, event, kFactor=None, kStd=None):
        # todo: pass kFactor as arguments, allowing for kLambda and kEta in one.
        # calculate aggregate flow based on gc record and measured flow from flowmeter.
        flowmeterID = event.getField('FlowmeterID')
        fmProps = self.getReaderRecord(flowmeterID)
        fmReader = fmProps['reader']
        tSettled = event.getField('tSettled')
        tEnd = event.getField('tEnd')
        # todo: change this field to match the new dataframe format.
        rdrInfo = self.getReaderRecord(flowmeterID)
        # eventDF = self.rawDask[fmReader].loc[lambda df: (tSettled <= df.index) & (df.index <= tEnd)].dropna(how='all').compute()
        settledDF =  eventDF.loc[lambda df: (tSettled <= df.index) & (df.index <= tEnd)].dropna(how='all')
        try:
            settledDF = settledDF[flowmeterID]
            settledDF = settledDF*rdrInfo['slope'] + rdrInfo['offset'] # flow output in SLPM, whole gas.



            kLambda = event.getField('KLambdaAvg') # use kLambda for thermal conductivity corrections.
            kLambdaStd = event.getField('KLambdaStd')
            flowAvg = settledDF.mean() # flow calculated is the flow read directly from the reader - no k factor involved.
            flowStd = settledDF.std()
            corrFlow = flowAvg * kLambda # corrected whole gas flow with GC composition involved.
            corrStd = (settledDF*kLambda).std()

            c1X = event.getField('C1MolFracAvg')
            c2X = event.getField('C2MolFracAvg')
            c3X = event.getField('C3MolFracAvg')
            ic4X = event.getField('iC4MolFracAvg')
            nc4X = event.getField('nC4MolFracAvg')
            ic5X = event.getField('iC5MolFracAvg')
            nc5X = event.getField('nC5MolFracAvg')
            c6X = event.getField('C6MolFracAvg')
            c4X = (ic4X+nc4X)
            thcX = (c1X + c2X + c3X + nc4X + ic4X + nc5X + ic5X + c6X)

            c1XStd = event.getField('C1MolFracStd')
            c2XStd = event.getField('C2MolFracStd')
            c3XStd = event.getField('C3MolFracStd')
            ic4XStd = event.getField('iC4MolFracStd')
            nc4XStd = event.getField('nC4MolFracStd')
            ic5XStd = event.getField('iC5MolFracStd')
            nc5XStd = event.getField('nC5MolFracStd')
            c6XStd = event.getField('C6MolFracStd')
            c4XStd = math.sqrt(ic4XStd ** 2 + nc4XStd ** 2)
            thcStd = math.sqrt(c1XStd ** 2 + c2XStd ** 2 + c3XStd ** 2 + ic4XStd ** 2 +
                               nc4XStd ** 2 + ic5XStd ** 2 + nc5XStd ** 2 + c6XStd ** 2)

            c1Flow = corrFlow * c1X
            c2Flow = corrFlow * c2X
            c3Flow = corrFlow * c3X
            ic4Flow = corrFlow * ic4X
            nc4Flow = corrFlow * nc4X
            c4Flow = ic4Flow + nc4Flow # butane is overall flow of iso and normal butane.
            thcFlow = corrFlow * thcX


            fmMax = fmProps['max']
            delM = fmMax/100 # for the GSHs, accuracy is +/- 1% full span. # todo: grab this from the actual value

            # note: following terms are normalized by aggregate property (squared)
            sigQSq = (flowStd/flowAvg) ** 2
            sigQM  = (flowStd*delM/(flowAvg ** 2))
            delMsq = (delM/(2*flowAvg)) ** 2
            sigKsq = (kLambdaStd/kLambda) ** 2

            delQ   = 2 * flowAvg * kLambda *       math.sqrt(sigQSq + sigQM + delMsq + sigKsq)
            delC1  = 2 * flowAvg * kLambda * c1X * math.sqrt(sigQSq + sigQM + delMsq + sigKsq + (c1XStd / c1X) ** 2)
            delC2  = 2 * flowAvg * kLambda * c2X * math.sqrt(sigQSq + sigQM + delMsq + sigKsq + (c2XStd / c2X) ** 2)
            delC3  = 2 * flowAvg * kLambda * c3X * math.sqrt(sigQSq + sigQM + delMsq + sigKsq + (c3XStd / c3X) ** 2)
            delC4  = 2 * flowAvg * kLambda * c4X * math.sqrt(sigQSq + sigQM + delMsq + sigKsq + (c4XStd / c4X) ** 2)
            delTHC = 2 * flowAvg * kLambda * thcX* math.sqrt(sigQSq + sigQM + delMsq + sigKsq + (thcStd / thcX) ** 2)

            event.addField("FlowAvg", corrFlow)
            event.addField("FlowStDev", corrStd)
            event.addField("FlowUncertainty", delQ)
            event.addField("C1FlowAvg", c1Flow)
            event.addField("C1FlowUncertainty", delC1)
            event.addField("C2FlowAvg", c2Flow)
            event.addField("C2FlowUncertainty", delC2)
            event.addField("C3FlowAvg", c3Flow)
            event.addField("C3FlowUncertainty", delC3)
            event.addField("C4FlowAvg", c4Flow)
            event.addField("C4FlowUncertainty", delC4)
            event.addField("THCFlowAvg", thcFlow)
            event.addField("THCFlowUncertainty", delTHC)
        except Exception as e:
            print(f"Could not process event due to error: {e}")

    def _qcFlowBounds(self, singleEvent):
        fmName = singleEvent.getField('FlowmeterID')
        tSettled = singleEvent.getField('tSettled')
        tEnd = singleEvent.getField('tEnd')
        rdrName = self.getReaderRecord(fmName)['reader']
        # eventDF = self.rawDataframe.loc[lambda df: (tSettled <= df.index) & (df.index <= tEnd)].dropna(how='all').compute()
        eventDF = self.rawDataframe.loc[lambda df: (tSettled <= df.index) & (df.index <= tEnd)].dropna(how='all')
        fmInfo = self._getSensorInfo(fmName)
        minSLPM = fmInfo['min'] # todo: put this calculation in too? min is usually 0, but what if it isn't?
        maxSLPM = fmInfo['max']
        fmSlope = fmInfo.get('slope',1) # using defaults of 1 and 0 for alicat flowmeters.
        fmOffset = fmInfo.get('offset',0)
        maxV = (maxSLPM - fmOffset) / fmSlope
        minBound = .1 * maxV + minSLPM
        maxBound = .9 * maxV
        dfExists = True
        try:
            if eventDF.empty:
                dfExists = False
        except Exception as e:
            if not eventDF:
                dfExists = False
        if dfExists and fmName in eventDF.columns:
            fmColumn = eventDF[fmName]
            minFlag = False
            maxFlag = False
            fmAbove = fmColumn.where(lambda v: v <= minBound).dropna(how='all')
            fmBelow = fmColumn.where(lambda v: v >= maxBound).dropna(how='all')
            if singleEvent.ActiveEPCount > 0:
                if len(fmAbove) > 0:
                    maxFlag = True
                if len(fmBelow) > 0:
                    minFlag = True
            if minFlag:
                addQCFlag(QC_FLAGS.METER_SPAN_MIN, singleEvent)
            if maxFlag:
                addQCFlag(QC_FLAGS.METER_SPAN_MAX, singleEvent)

    def _isRefEmission(self, singleEmission):
        activeEP = singleEmission.ActiveEPCount
        if activeEP == 0:
            return False
        epID = singleEmission.EPID
        epFlowLevel = singleEmission.EPFlowLevel
        refsMatching = self.automatedEventFlags.get(epID, {}).get(epFlowLevel, [])
        if not refsMatching:
            return False
        for ref in refsMatching:
            if abs(ref['timestamp']-singleEmission.tStart) < 2 and singleEmission.Duration > BEST_ESTIMATE_THRESHOLD:
                return True # this event matches an existing event within a margin of error
        return False


    def _findExpEvents(self):
        # add all cals to the experiment info events based on experiment ID.
        for expID, expInfo in self.importedExperimentsByID.items():
            expInfo['cals'] = []
            relevantCals = list(filter(lambda x: x['expID'] == expID, self.importedCalEvents))
            if relevantCals:
                # find all start and end cals, sorted by the timestamps
                startCals = sorted(list(filter(lambda x: x['eventType'] == EventTypes.CalStart, relevantCals)), key=lambda x:x['timestamp'])
                endCals = sorted(list(filter(lambda x: x['eventType'] == EventTypes.CalEnd, relevantCals)), key=lambda x: x['timestamp'])
                for startCal in startCals:
                    corrEnd = list(filter(lambda x: x['timestamp'] >= startCal['timestamp'], endCals))
                    if corrEnd:
                        expInfo['cals'].append({"start": startCal, "end": corrEnd[0], "emissions": []})
            expInfo['events'] = list(filter(lambda x: x['expID'] == expID, self.importedEmissionEvents))

    def getTrueEP(self, emissionEvent):
        lastCol = sorted(emissionEvent['SetStates'].keys())[-1]
        lastColState = emissionEvent["SetStates"][lastCol]
        evState = "A" if int(lastColState) == 1 else "B"
        epInfo = self.epRecord.where(lambda df:
                                     (df['CB']==emissionEvent['Controller']) &
                                     (df['EV'] == lastCol) &
                                     (df['Active'].astype(int) == 1) &
                                     (df['EV State'] == evState)).dropna(how='all')
        return epInfo.iloc[0]['Emission Point']


    def _filterEmissionEvents(self):
        incorrectEps = {}
        for emissionEvent in self.importedEmissionEvents:
            ts = emissionEvent['timestamp']
            expID = emissionEvent['expID']
            expEPID = emissionEvent['EmissionPoint']
            trueEPID = self.getTrueEP(emissionEvent)
            if not trueEPID == expEPID:
                if not expEPID in incorrectEps:
                    incorrectEps[expEPID] = {
                        "expEPID": expEPID,
                        "trueEPID": trueEPID,
                        'expID': expID
                    }
                epID = trueEPID
            else:
                epID = expEPID
            fl = emissionEvent['FlowLevel']
            if expID in self.importedExperimentsByID.keys():
                expInfo = self.importedExperimentsByID[expID]
                corrCal = list(filter(lambda x: x['start']['timestamp']<= ts and x['end']['timestamp'] >= ts, expInfo['cals']))
                if corrCal and fl > 0:
                    corrCal[0]['emissions'].append(emissionEvent)
                    if not epID in self.automatedEventFlags:
                        self.automatedEventFlags[epID] = {}
                    if not fl in self.automatedEventFlags[epID]:
                        self.automatedEventFlags[epID][fl] = []
                    self.automatedEventFlags[epID][fl].append(emissionEvent)
                if not epID in self.allEmissionEvents:
                    self.allEmissionEvents[epID] = {}
                if not fl in self.allEmissionEvents[epID]:
                    self.allEmissionEvents[epID][fl] = []
                self.allEmissionEvents[epID][fl].append(emissionEvent)
        for d in incorrectEps.values():
            logging.info(f'Discrepancy between experiment and actual EP according to config.'
                     f'\n\t Experiment ID: {d["expID"]}'
                     f'\n\t Experiment EP: {d["expEPID"]}'
                     f'\n\t Config EP:     {d["trueEPID"]}'
                     f'')

    def _getRefEvent(self, singleEmission):
        """Return the reference event or single event that was run alone for the start time closest to the start time of this event."""
        activeEPs = singleEmission.ActiveEPCount
        epID = singleEmission.EPID
        epFlowLevel = singleEmission.EPFlowLevel
        if activeEPs == 1 and singleEmission.Duration > BEST_ESTIMATE_THRESHOLD:
            return singleEmission
        anyRefs = self.referenceEmissions.get(epID, {}).get(epFlowLevel, [])
        singleRefEvents = list(filter(lambda x: not x.ActiveEPCount > 1, anyRefs))
        determinateRefs = list(filter(lambda x: not x.BFT == "IndeterminateEvent", singleRefEvents))
        if determinateRefs:
            sortedByStart = sorted(determinateRefs, key=lambda x: abs(x.tStart - singleEmission.tStart))
            return sortedByStart[0] # return the event with the start time that is closest to this start time.
        anySingles = self.loneEmissions.get(epID, {}).get(epFlowLevel, [])
        determinateSingles =  list(filter(lambda x: not x.BFT == "IndeterminateEvent", anySingles))
        if determinateSingles:
            sortedByStart = sorted(determinateSingles, key=lambda x: abs(x.tStart - singleEmission.tStart))
            return sortedByStart[0] # return the event with the start time that is closest to this start time.
        raise CalExistsError

    def _getLinkedEvent(self, singleEmission):
        """Returns the event linked to this current emission based on the timestamp. If no linked emissions exist, find
        the most recent valve event linked to this emission. """
        epID = singleEmission.EPID
        epFlowLevel = singleEmission.EPFlowLevel
        emsMatching = self.allEmissionEvents.get(epID, {}).get(epFlowLevel, [])
        if singleEmission.ActiveEPCount >0:
            i=-10
        if not emsMatching:
            return None
        prevEms = sorted(emsMatching, key=lambda x:abs(x['timestamp'] - singleEmission.tTransitioned))
        if prevEms:
            return prevEms[0]
        return None

    def addRefEmission(self, singleEmission):
        epID = singleEmission.EPID
        epFlowLevel = singleEmission.EPFlowLevel
        if not epID in self.referenceEmissions:
            self.referenceEmissions[epID] = {}
        if not epFlowLevel in self.referenceEmissions[epID]:
            self.referenceEmissions[epID][epFlowLevel] = []
        if not singleEmission in self.referenceEmissions[epID][epFlowLevel]:
            self.referenceEmissions[epID][epFlowLevel].append(singleEmission)

    def addLoneEmission(self, singleEmission):
        epID = singleEmission.EPID
        epFlowLevel = singleEmission.EPFlowLevel
        if not epID in self.loneEmissions:
            self.loneEmissions[epID] = {}
        if not epFlowLevel in self.loneEmissions[epID]:
            self.loneEmissions[epID][epFlowLevel] = []
        if not singleEmission in self.loneEmissions[epID][epFlowLevel]:
            self.loneEmissions[epID][epFlowLevel].append(singleEmission)