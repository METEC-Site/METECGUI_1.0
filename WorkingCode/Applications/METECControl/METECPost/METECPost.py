import os
import datetime
from enum import Enum, auto
import logging

import pandas as pd

import Utils.FileUtils as fUtils
import Utils.TimeUtils as tu
from Applications.METECControl.METECPost.Classes import MRFactory, MetaRecord
from Applications.METECControl.METECPost.Writing import writeAllData, writeControlledReleases, copyNotes
from Applications.METECControl.METECPost.loading import ARGS_METADATA, loadPostComponents, loadDF, cleanTempFolder, getNextArchive, N_PARTITIONS
from Applications.METECControl.METECPost import Helpers as hp
from Applications.METECControl.METECPost.ExperimentSummarizer import runPostProcessing
from Framework.Archive.DirectoryArchiver import daFromArchive
from Framework.BaseClasses.Registration.ObjectRegister import Registry

DEBUG_MODE = False
WHOLE_EXPERIMENTS = True #EWE changed this to True from False
# todo: fix where rows have missing values!!! See Archive 2021-01-15 for an example of this!

class TransitionModes(Enum):
    OFF_TO_ON  = auto()
    ON_TO_OFF  = auto()
    ON_TO_ON   = auto() # an unstable period
    OFF_TO_OFF = auto() # Likely will never happen, but keeping it for completeness sake.

def main(rManifest=None, epManifest=None, fmManifest=None, gc=None, weather=None, archive=None, minSettlingTime=None, overrideLoggerLevel=True):
    # set the scheduler type for dask to be single threaded - helpful for debugging.
    # also helps not overload memory.
    # dask.config.set(scheduler='single-threaded')
    # client = ddist.Client()
    # setting logging
    if overrideLoggerLevel:
        logging.getLogger().setLevel(logging.INFO)


    # The following are in summary form (Datetime of start of record; record itself; notes; filepath; other info):
    # readerRecords: (slope, intercept, pin, etc) info per reader (IE controller box)
    # epRecords: Emission Point records of the site.
    # fmRecords: Flow Meter Records of the site.
    # gcRecords: Gas Chromatography records of the site.
    # archive: singular archive at the specified

    
    readerRecords, epRecords, fmRecords, gcRecords, weatherData, archive, minSettlingTime = loadPostComponents(rManifest, epManifest, fmManifest, gc, weather, archive, minSettlingTime)

    postProcess(readerRecords, epRecords, fmRecords, gcRecords, weatherData, archive, minSettlingTime)

def postProcess(readerRecords, epRecords, fmRecords, gcRecords, weatherData, archive, minSettlingTime):
    logging.info('Starting PostProcessing.')
    postStart = tu.nowEpoch()

    startExperimentT, endExperimentT, allCompleteEvents, pdDF, unstartedEvents, unfinishedEvents = loadDF(archive, wholeExperiments=WHOLE_EXPERIMENTS)
    # startExperimentT, endExperimentT, allCompleteEvents, pdDF, unstartedEvents, unfinishedEvents = loadDF(archive, asDask=True, debugMode=DEBUG_MODE, wholeExperiments=WHOLE_EXPERIMENTS)
    nextArchivePath = getNextArchive(archive)
    if unfinishedEvents and not nextArchivePath is None:
        nextArchive = daFromArchive(nextArchivePath, name=nextArchivePath.name, readonly=True)
        nextArchiveFirstEventTime, nextArchiveLastEventEnd, nextLoadedEvents, nextDF, nextDFUnstartedEvents, nextDFUnfinishedEvents = loadDF(nextArchive, wholeExperiments=WHOLE_EXPERIMENTS)

        crossoverExpIDs = []
        crossoverEvents = []
        for unstartedEvent in nextDFUnstartedEvents:
            for unfinishedEvent in unfinishedEvents:
                if unfinishedEvent['expID'] == unstartedEvent['expID']:
                    crossoverExpIDs.append(unstartedEvent['expID'])
                    crossoverEvents.append(unfinishedEvent)
                    crossoverEvents.append(unstartedEvent)
        for crossoverEvent in crossoverEvents:
            if not crossoverEvent in allCompleteEvents:
                allCompleteEvents.append(crossoverEvent)
        allCompleteEvents = list(sorted(allCompleteEvents, key= lambda x: x['timestamp']))
        if allCompleteEvents:
            lastTimestamp = allCompleteEvents[-1]['timestamp']
            if lastTimestamp < list(pdDF.index)[-1]:
                lastTimestamp = list(pdDF.index)[-1]

            # pdDF = pdDF.append(nextDF)
            pdDF = pd.concat([pdDF,nextDF])

            pdDF = pdDF[(pdDF.index <= lastTimestamp)]

    hp.correctReaderRecords(readerRecords, pdDF)

    Metarecords = MRFactory(pdDF, readerRecords, epRecords, fmRecords, gcRecords, allCompleteEvents, minSettlingTime)
    vts = []
    for mr in Metarecords:
        vts.append(mr.flagValveTransitions()) # flags are stored in the Metarecord as a self variable. They are any time a valve changes from one state to another.
        mr.flagExperimentZeros()
        mr.processFlags() # main method that applies cals, ep configs, etc.
    for mr in Metarecords:
        mr.linkExpIDs()
        mr.integrateRefs() # find all relevant reference emissions and add them to the appropriate dictionaries
    for mr in Metarecords:
        mr.linkRefs()      # link all emissions to their own reference emissions.
        mr.linkIntents()
        mr.applyEstimates()
        mr.applyQC() # todo: incorporate the eventDF. Maybe by moving this into the processFlags method?

    allEmissions = list(sorted(MetaRecord.allEmissions, key=lambda x: x.getField('tStart'))) # get the class emissions.

    # outputFolder = os.path.join(archive.archivePath, "post", f"{tu.dtToStr(tu.nowDT(),'%Y-%m-%d_%H-%M-%S')}")
    outputFolder = os.path.join(archive.archivePath, "post", f"{tu.dtToStr(tu.nowDT(), '%Y-%m-%d_%H-%M-%S')}")
    if not os.path.exists(outputFolder):
        os.makedirs(outputFolder)
    timeseriesFolder = os.path.join(outputFolder, "timeseries")
    if not os.path.exists(timeseriesFolder):
        os.makedirs(timeseriesFolder)
    summaryFolder = os.path.join(outputFolder, "summaries")
    if not os.path.exists(summaryFolder):
        os.makedirs(summaryFolder)

    releasesDF = writeControlledReleases(allEmissions, summaryFolder)
    sensorDF, manifoldDF, metDF, miscDF = writeAllData(Metarecords, timeseriesFolder)
    runPostProcessing(releasesDF, metDF, "", summaryFolder)

    copyNotes(outputFolder)

    logging.info(f'\nCompleted Analysis:'
                 f'\n\tTotal Seconds: {tu.nowEpoch() - postStart}')
    Registry.endRegistry()
    MetaRecord.reinitializeClassVariables()


if __name__ == '__main__':
    args = fUtils.getArgs(ARGS_METADATA)
    main(args.RManifest, args.EPManifest, args.FMManifest, args.GC, args.weather, args.archive, args.minSettlingTime)