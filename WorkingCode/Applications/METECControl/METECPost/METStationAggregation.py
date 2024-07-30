import pandas as pd
import pathlib
import json
import logging
import datetime
import pytz

# relevant paths for slope/offset of all readers for the MET data. Should be changed RARELY.
readerRecordPath = "D:\\SVNs\\METEC_SVN\\Facility Operations\\ConfigurationAndCalibrationRecords\\ReaderRecords\\SiteConfig-20240115.json"
# folder in which all archives will be checked
# rootFolderPath = pathlib.Path("R:\\_RawData\\Continuous") # path to backup/continuous files of just the MET data.
rootFolderPath = pathlib.Path("R:\\_Archives") #note: this is the other place where archives are stored. If data seems to be missing, try this one instead.
outputFolder = pathlib.Path("R:\\MET data") # output csv destination folder.

dateStart = "20240409_000000" # start time IN LOCAL that will begin the search
dateEnd = '20240410_000000' # end time IN LOCAL that will end the search.
startDT = datetime.datetime.strptime(dateStart, "%Y%m%d_%H%M%S").astimezone(pytz.timezone('America/Denver'))
startEpoch = startDT.timestamp()
dayBeforeStartDT = startDT-datetime.timedelta(days=1) # subtracting one day to make sure all relevant data is fetched.
endDT = datetime.datetime.strptime(dateEnd, "%Y%m%d_%H%M%S").astimezone(pytz.timezone('America/Denver'))
endEpoch = endDT.timestamp()
met1OutputPath = outputFolder.joinpath(f'{startDT.strftime("%Y%m%d")}-{endDT.strftime("%Y%m%d")}_MET-1.csv')
met2OutputPath = outputFolder.joinpath(f'{startDT.strftime("%Y%m%d")}-{endDT.strftime("%Y%m%d")}_MET-2.csv')

allMet1Paths = []
allMet2Paths = []

for singleFolder in rootFolderPath.iterdir():
    try:
        folderDate = datetime.datetime.strptime(singleFolder.name, '%Y-%m-%d_%H-%M-%S').astimezone(pytz.timezone('UTC'))
        if dayBeforeStartDT < folderDate and folderDate < endDT: # using dayBefore... to include data that might have been in the previous day before rollover.
            dataFolder = singleFolder.joinpath('data')
            # find all paths in the data folder associated with the correponsing met stations.
            met1DataPaths = list(filter(lambda x: "MET-1" in x.name and not 'corr' in x.name and '.csv' in x.name, dataFolder.iterdir()))
            met2DataPaths = list(filter(lambda x: "MET-2" in x.name and not 'corr' in x.name and '.csv' in x.name, dataFolder.iterdir()))
            allMet1Paths = [*allMet1Paths, *met1DataPaths]
            allMet2Paths = [*allMet2Paths, *met2DataPaths]
    except Exception as e:
        logging.exception(f'Could not parse data in folder {singleFolder} due to exception {e}')

met1DFs = []
met2DFs = []

allMet1Paths.sort(key=lambda x: int(x.name.split('_')[1].split('.')[0])) # sort based on the UTC timestamp appended to the name. (EX: MET-1.LJ-1_{TIMESTAMP}.csv
allMet2Paths.sort(key=lambda x: int(x.name.split('_')[1].split('.')[0])) # sort based on the UTC timestamp appended to the name. (EX: MET-2.LJ-1_{TIMESTAMP}.csv

for met1DataPath in allMet1Paths:
    try:
        with met1DataPath.open(mode='r', newline='') as f:
            headerDF = pd.read_csv(f,nrows=0)
        with met1DataPath.open(mode='r', newline='') as f: # originally had these 'opens' happen at the same time, but it skipped data.
            df = pd.read_csv(f,skiprows=2, names=[h for h in headerDF.keys()])
            df.dropna(how="any", inplace=True)
            met1DFs.append(pd.concat([headerDF,df]))
        del headerDF
        del df
    except Exception as e:
        logging.error(f'Could not load in file {str(met1DataPath)} due to exception {e}')

for met2DataPath in allMet2Paths:
    try:
        with met2DataPath.open(mode='r', newline='') as f:
            headerDF = pd.read_csv(f,nrows=0)
        with met2DataPath.open(mode='r', newline='') as f: # originally had these 'opens' happen at the same time, but it skipped data.
            df = pd.read_csv(f,skiprows=2, names=[h for h in headerDF.keys()])
            df.dropna(how="any", inplace=True)
        met2DFs.append(pd.concat([headerDF,df]))
        del headerDF
        del df
    except Exception as e:
        logging.error(f'Could not load in file {str(met2DataPath)} due to exception {e}')

finalMET1DF = pd.concat(met1DFs)
for df in met1DFs:
    del df
del met1DFs
finalMET1DF.set_index('timestamp', inplace=True)
finalMET1DF = finalMET1DF.loc[finalMET1DF.index.to_series().between(startEpoch, endEpoch)]

finalMET2DF = pd.concat(met2DFs)
for df in met2DFs:
    del df
del met2DFs
finalMET2DF.set_index('timestamp', inplace=True)
finalMET2DF = finalMET2DF.loc[finalMET2DF.index.to_series().between(startEpoch, endEpoch)]

with open(readerRecordPath) as readerJson:
    rr = json.load(readerJson)
    met1Rec = rr['MET-1.LJ-1']
    for colName in finalMET1DF.columns:
        if not "GND" in colName and not 'timestamp' in colName:
            colProps = met1Rec['fields'][colName]
            finalMET1DF[colName] = (finalMET1DF[colName] - finalMET1DF['GND'])*colProps['slope'] + colProps['offset']
    met2Rec = rr['MET-2.LJ-1']
    for colName in finalMET2DF.columns:
        if not "GND" in colName and not 'timestamp' in colName:
            colProps = met2Rec['fields'][colName]
            finalMET2DF[colName] = (finalMET2DF[colName] - finalMET2DF['GND'])*colProps['slope'] + colProps['offset']
finalMET1DF.to_csv(met1OutputPath)
finalMET2DF.to_csv(met2OutputPath)