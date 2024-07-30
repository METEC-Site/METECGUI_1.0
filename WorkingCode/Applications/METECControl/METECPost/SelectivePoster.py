import datetime
import pathlib
import pytz
import time
import os
import shutil
import logging
from logging import config
import json
from Applications.METECControl.METECPost import METECPost
from Framework.BaseClasses.Registration import ObjectRegister
from Utils import TimeUtils as tu


archiveRootFolder = pathlib.Path("R:\_Archives")
dateStart = "20231214_000000" # start time IN LOCAL that will begin the search
dateEnd = '20231218_000000' # end time IN LOCAL that will end the search.
startDT = datetime.datetime.strptime(dateStart, "%Y%m%d_%H%M%S").astimezone(pytz.timezone('America/Denver'))
startEpoch = startDT.timestamp()
endDT = datetime.datetime.strptime(dateEnd, "%Y%m%d_%H%M%S").astimezone(pytz.timezone('America/Denver'))
endEpoch = endDT.timestamp()

defaultArgs = {
    "archive":None,
    "gc": "C:\\Users\\METEC\\Documents\\SVN_METEC\\Operations\\ConfigurationAndCalibrationRecords\\GasCompositions\\GCRecords\\GasCompositionSummary.csv",
    "rManifest": "C:\\Users\\METEC\\Documents\\SVN_METEC\\Operations\\ConfigurationAndCalibrationRecords\\ReaderRecords\\ReaderSummary.csv",
    "epManifest": "C:\\Users\\METEC\\Documents\\SVN_METEC\\Operations\\ConfigurationAndCalibrationRecords\\EmissionPointConfigurations\\EPConfigSummary.csv",
    "fmManifest": "C:\\Users\\METEC\\Documents\\SVN_METEC\\Operations\\ConfigurationAndCalibrationRecords\\FlowMeterConfigurations\\FMConfigSummary.csv",
    "minSettlingTime": 120
}
correctArchivePaths = list(filter(lambda x: (datetime.datetime.strptime(x.name, '%Y-%m-%d_%H-%M-%S').astimezone(pytz.timezone('UTC')) >= startDT) and
                                            (datetime.datetime.strptime(x.name, '%Y-%m-%d_%H-%M-%S').astimezone(pytz.timezone('UTC')) < endDT),
                                             list(archiveRootFolder.iterdir())))
sortedArchivePaths = sorted(list(correctArchivePaths), key=lambda x: x.name)

for archivePath in sortedArchivePaths:
    try:
        folderDate = datetime.datetime.strptime(archivePath.name, '%Y-%m-%d_%H-%M-%S').astimezone(pytz.timezone('UTC'))
        if startDT < folderDate and folderDate < endDT: # using dayBefore... to include data that might have been in the previous day before rollover.
            thisArchiveArgs = {**defaultArgs}
            thisArchiveArgs['archive'] = archivePath
            METECPost.main(**thisArchiveArgs, overrideLoggerLevel=False)
    except Exception as e:
        logging.exception(f'Could not post archive {archivePath} due to exception {e}')
        ObjectRegister.Registry.endRegistry()
        METECPost.MetaRecord.reinitializeClassVariables()