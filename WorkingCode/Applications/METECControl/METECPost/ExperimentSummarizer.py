import argparse
import logging
import math
import os

import dask.dataframe
import pandas as pd

UTC_FORMAT = "%Y-%m-%d_%H:%M:%S"
EMISSION_CATEGORIES = ['Pre Test', "Post Test", "Vent", "Fugitive"]

base_expSummaryDF = pd.DataFrame(columns=['ExperimentID', 'StartTimestamp', 'EndTimestamp', 'EPCount',
       'AvgTHCFlowRate', 'WindSpeedAvg', 'WindSpeedStd', 'WindDirAvg',
       'WindDirStd', 'TAtmAvg', 'TAtmStd', 'PAtmAvg', 'PAtmStd', 'Type',
       'PreCal', 'PostCal', 'PreCalStartTimestamp', 'PreCalEndTimestamp',
       'MainStartTimestamp', 'MainEndTimestamp', 'PostCalStartTimestamp',
       'PostCalEndTimestamp'])
base_epSummaryDF = pd.DataFrame(columns=['ExperimentID', 'EPID', 'Latitude', 'Longitude', 'Altitude', 'EquipmentUnitID', 'EquipmentGroupID', 'EmissionCategory',
                                         'EmissionIntent', 'EPBFE', 'EPBFU', 'EPDutyCycle', 'QCFlags', 'C1MassFlow', 'C1MassFlowUncertainty', 'C2MassFlow',
                                         'C2MassFlowUncertainty', 'C3MassFlow', 'C3MassFlowUncertainty', 'C4MassFlow', 'C4MassFlowUncertainty', 'C5MassFlow',
                                         'C5MassFlowUncertainty', 'C6MassFlow', 'C6MassFlowUncertainty'])



C_MASS = 12.0107  # https://webbook.nist.gov/cgi/cbook.cgi?ID=C7440440&Units=SI
H_MASS = 1.00794  # https://webbook.nist.gov/cgi/cbook.cgi?Name=hydrogen&Units=SI

#  https://webbook.nist.gov/cgi/cbook.cgi?ID=C74828&Units=SI

cNumToMass = {
    1: 1 * C_MASS + 4 * H_MASS,
    2: 2 * C_MASS + 6 * H_MASS,
    3: 3 * C_MASS + 8 * H_MASS,
    4: 4 * C_MASS + 10 * H_MASS,
    5: 5 * C_MASS + 12 * H_MASS,
    6: 6 * C_MASS + 14 * H_MASS
}


def calculateMassFlow(v, numCarbon):
    """
    v: volume in SLPM
    """
    Mw = cNumToMass[numCarbon]
    p = 101325  # Pa,
    t = 294.15  # K
    R = 8.31446261815324
    unitConversionFactor = 0.06  # (m^3/hr) / (slpm)
    return p * v * unitConversionFactor * Mw / (R * t)


def yamartinoMethod(wind):
    n = len(wind)
    if n > 0:
        s = 1 / n * sum([math.sin(angle) for angle in wind])
        c = 1 / n * sum([math.cos(angle) for angle in wind])
        avg = math.atan2(s, c)
        epsilon = math.sqrt(1 - (s ** 2 + c ** 2))
        stdDev = math.asin(epsilon) * (1 + (2 / math.sqrt(3) - 1) * epsilon ** 3)
        return math.degrees(avg), math.degrees(stdDev)
    else:
        return 0, 0


def getExpSummaryRow(controlledReleasesDF, metDF, expID, epSum):
    df = controlledReleasesDF.loc[controlledReleasesDF['ExperimentID'] == expID]
    epSum = epSum.loc[epSum['ExperimentID'] == expID]
    startTime = int(df['tStart'].values[0]) # start time
    endTime = int(df['tEnd'].values[-1])  # end time
    epCount = len(df['EPID'].unique())  # ep count
    flowSum = epSum[['C1MassFlow', 'C2MassFlow', 'C3MassFlow', 'C4MassFlow', 'C5MassFlow', 'C6MassFlow']].sum(axis=1) * epSum['EPDutyCycle'] / 100
    avgFlow = flowSum.mean()
    #wind
    metDF = metDF[((startTime<=metDF.index) & (metDF.index <= endTime))]
    if type(metDF) is dask.dataframe.core.DataFrame:
        metDF = metDF.compute()
    windSpeedData = metDF["MET-1.WS"]
    tempData = metDF["MET-1.AT"]
    pressureData = metDF["MET-1.BP"]
    windDirData = metDF["MET-1.WD"]
    windDirData = windDirData.dropna()
    windDirAvg, windDirStd = yamartinoMethod(windDirData)
    if windDirAvg < 0:
        windDirAvg = 360 + windDirAvg
    #temp/pressure


    mainExperimentDF = df.loc[~df['EmissionCategory'].isin(['Pre Test', 'Post Test'])]
    try:
        try:
            mainStart = mainExperimentDF['tStart'].values[0]
        except Exception as e:
            mainStart = None
        try:
            mainEnd = mainExperimentDF['tEnd'].values[0]
        except Exception as e:
            mainEnd = None

        preCal, postCal = False, False
        preCalStart, preCalEnd, postCalStart, postCalEnd = None, None, None, None
        preCalDF = df.loc[df['EmissionCategory'] == 'Pre Test']
        if len(preCalDF) > 0:
            preCal = True
            preCalStart = preCalDF['tStart'].values[0]
            preCalEnd = preCalDF['tEnd'].values[-1]

        postCalDF = df.loc[df['EmissionCategory'] == 'Post Test']
        if len(postCalDF) > 0:
            postCal = True
            postCalStart = postCalDF['tStart'].values[0]
            postCalEnd = postCalDF['tEnd'].values[-1]

        types = df['EmissionCategory'].unique()
        if 'adhoc' in types:
            expType = 'adhoc'
        else:
            expType = 'automated'

        rowData = {
            'ExperimentID': expID,
            'StartTimestamp': startTime,
            'EndTimestamp': endTime,
            'EPCount': epCount,
            'AvgTHCFlowRate': avgFlow,
            'WindSpeedAvg': windSpeedData.mean(),
            'WindSpeedStd': windSpeedData.std(),
            'WindDirAvg': windDirAvg,
            'WindDirStd': windDirStd,
            'TAtmAvg': tempData.mean(),
            'TAtmStd': tempData.std(),
            'PAtmAvg': pressureData.mean(),
            'PAtmStd': pressureData.std(),
            'Type': expType,
            'PreCal': preCal,
            'PostCal': postCal,
            'PreCalStartTimestamp': preCalStart,
            'PreCalEndTimestamp': preCalEnd,
            'MainStartTimestamp': mainStart,
            'MainEndTimestamp': mainEnd,
            'PostCalStartTimestamp': postCalStart,
            'PostCalEndTimestamp': postCalEnd
        }
        return rowData
    except Exception as e:
        logging.info(f'Could not add row for experiment ID due to exception: {e}')
        return None


def getExpSummary(crDF, metDF, epSum):
    expSummaryDF = base_expSummaryDF.copy(True)
    for eID in crDF['ExperimentID'].unique():
        try:
            isNan = math.isnan(eID)
        except:
            isNan = False
        if eID != '' and not isNan:
            expSummaryRow = getExpSummaryRow(crDF, metDF, eID, epSum)
            if expSummaryRow:
                expSummaryDF = pd.concat([expSummaryDF, pd.DataFrame(expSummaryRow, index=[0])], ignore_index=True)
    return expSummaryDF


def getEPSummaryRows(expID, controlledReleasesDF):
    rows = []
    df = controlledReleasesDF.loc[controlledReleasesDF['ExperimentID'] == expID].copy()
    mainExperimentDF = df.loc[~df['EmissionCategory'].isin(['Pre Test', 'Post Test'])]
    if len(mainExperimentDF.index) > 0:
        startTime = mainExperimentDF['tStart'].values[0]  # start time
        endTime = mainExperimentDF['tEnd'].values[-1]
        mainExperimentLength = endTime-startTime
    else:
        mainExperimentLength = None

    intents = df['EmissionIntent'].unique()
    types = df['EmissionCategory'].unique()
    for intent in intents:
        for category in types:
            intentDF = df.loc[df['EmissionIntent'] == intent]
            categoryDF = intentDF.loc[intentDF['EmissionCategory'] == category]
            uniqueEPs = categoryDF['EPID'].unique()
            uniqueEPs = [ep for ep in uniqueEPs if type(ep) is str]
            sums = {ep: {"BFE": 0, "BFU": 0, "durationSum": 0, 'QCFlags': 0, 'c1': 0, 'c2': 0, 'c3': 0, 'c4': 0, 'c5': 0, 'c6': 0, 'c1U': 0,
                         'c2U': 0, 'c3U': 0, 'c4U': 0, 'c5U': 0, 'c6U': 0} for ep in uniqueEPs}
            if len(uniqueEPs) > 0:
                for i, row in categoryDF.iterrows():
                    ep = row['EPID']
                    if type(ep) is str and len(ep) > 0:
                        flowEst = float(row['BFE']) if row['BFE'] else 0
                        flowUnc = float(row['BFU']) if row['BFU'] else 0
                        sums[ep]['BFE'] += flowEst * row['Duration']
                        sums[ep]['BFU'] += flowUnc * row['Duration']
                        sums[ep]['durationSum'] += row['Duration']
                        sums[ep]['QCFlags'] = sums[ep]['QCFlags'] | int(str(row['QCFlags']), 2)
                        sums[ep]['c1'] += calculateMassFlow(flowEst * row['Duration'] * ( row['C1MolFracAvg'] ), 1)
                        sums[ep]['c2'] += calculateMassFlow(flowEst * row['Duration'] * ( row['C2MolFracAvg'] ), 2)
                        sums[ep]['c3'] += calculateMassFlow(flowEst * row['Duration'] * ( row['C3MolFracAvg'] ), 3)
                        sums[ep]['c4'] += calculateMassFlow(flowEst * row['Duration'] * ( row['nC4MolFracAvg'] + row['iC4MolFracAvg'] ), 4)
                        sums[ep]['c5'] += calculateMassFlow(flowEst * row['Duration'] * ( row['nC5MolFracAvg'] + row['iC5MolFracAvg'] ), 5)
                        sums[ep]['c6'] += calculateMassFlow(flowEst * row['Duration'] * ( row['C6MolFracAvg'] ), 6)
                        sums[ep]['c1U'] += calculateMassFlow(flowUnc * row['Duration'] * ( row['C1MolFracAvg'] ), 1)
                        sums[ep]['c2U'] += calculateMassFlow(flowUnc * row['Duration'] * ( row['C2MolFracAvg'] ), 2)
                        sums[ep]['c3U'] += calculateMassFlow(flowUnc * row['Duration'] * ( row['C3MolFracAvg'] ), 3)
                        sums[ep]['c4U'] += calculateMassFlow(flowUnc * row['Duration'] * ( row['nC4MolFracAvg'] + row['iC4MolFracAvg'] ), 4)
                        sums[ep]['c5U'] += calculateMassFlow(flowUnc * row['Duration'] * ( row['nC5MolFracAvg'] + row['iC5MolFracAvg'] ), 5)
                        sums[ep]['c6U'] += calculateMassFlow(flowUnc * row['Duration'] * ( row['C6MolFracAvg'] ), 6)
                for key, value in sums.items():
                    dutyCycle = value['durationSum']/mainExperimentLength * 100 if mainExperimentLength else 0
                    epRow = {
                        'ExperimentID': expID,
                        'EPID': key,
                        'Latitude': categoryDF.loc[categoryDF['EPID'] == key, 'EPLatitude'].iloc[0],
                        'Longitude': categoryDF.loc[categoryDF['EPID'] == key, 'EPLongitude'].iloc[0],
                        'Altitude': categoryDF.loc[categoryDF['EPID'] == key, 'EPAltitude'].iloc[0],
                        'EquipmentUnitID': categoryDF.loc[categoryDF['EPID'] == key, 'EPEquipmentUnit'].iloc[0],
                        'EquipmentGroupID': categoryDF.loc[categoryDF['EPID'] == key, 'EPEquipmentGroup'].iloc[0],
                        'EmissionCategory': category,
                        'EmissionIntent': intent,
                        'EPBFE': value['BFE'] / value['durationSum'],
                        'EPBFU': value['BFU'] / value['durationSum'],
                        'EPDutyCycle': dutyCycle,
                        'QCFlags': "{0:b}".format(value['QCFlags']),
                        'C1MassFlow': value['c1'] / value['durationSum'],
                        'C1MassFlowUncertainty': value['c1U'] / value['durationSum'],
                        'C2MassFlow': value['c2'] / value['durationSum'],
                        'C2MassFlowUncertainty': value['c2U'] / value['durationSum'],
                        'C3MassFlow': value['c3'] / value['durationSum'],
                        'C3MassFlowUncertainty': value['c3U'] / value['durationSum'],
                        'C4MassFlow': value['c4'] / value['durationSum'],
                        'C4MassFlowUncertainty': value['c4U'] / value['durationSum'],
                        'C5MassFlow': value['c5'] / value['durationSum'],
                        'C5MassFlowUncertainty': value['c5U'] / value['durationSum'],
                        'C6MassFlow': value['c6'] / value['durationSum'],
                        'C6MassFlowUncertainty': value['c6U'] / value['durationSum'],
                    }
                    rows.append(epRow)
    return rows


def getEPSummary(crDF):
    crDF = crDF.fillna('')
    crDF = crDF.drop(crDF[crDF['EPID'] == ''].index)
    epSummaryDF = base_epSummaryDF.copy(True)
    for expID in crDF['ExperimentID'].unique():
        try:
            isNan = math.isnan(expID)
        except:
            isNan = False
        if expID != '' and not isNan:
            epSummaryDF = pd.concat([epSummaryDF, pd.DataFrame(getEPSummaryRows(expID, crDF))], ignore_index=True)
    return epSummaryDF


def runPostProcessing(controlledReleases, met, datetime, outputFolder):
    if type(controlledReleases) is str:
        crDF = pd.read_csv(controlledReleases)
    if type(met) is str:
        metDF = pd.read_csv(met)
    if type(controlledReleases) is pd.DataFrame:
        crDF = controlledReleases
    if type(met) is pd.DataFrame or pd.DataFrame:
        metDF = met
    if type(controlledReleases) is dask.dataframe.core.DataFrame:
        crDF = controlledReleases.compute()
    if type(met) is dask.dataframe.core.DataFrame:
        metDF = met
    if 'timestamp' in metDF.columns:
        metDF = metDF.dropna(subset=['timestamp'])
        metDF = metDF.set_index('timestamp')
    epSum = getEPSummary(crDF)
    expSum = getExpSummary(crDF, metDF, epSum)
    expSum:pd.DataFrame
    expSumPath = os.path.join(outputFolder, 'ExperimentSummary'+datetime+'.csv')
    expSum.to_csv(expSumPath, index=False)
    epSumPath = os.path.join(outputFolder, 'EPSummary'+datetime+'.csv')
    epSum.to_csv(epSumPath, index=False)
    print("Successfully wrote files:\n", expSumPath, '\n', epSumPath)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(dest="controlledReleasesPath", help="Path to controlled releases file.")
    parser.add_argument(dest="metPath", help="Path to MET file.")
    parser.add_argument(dest="outputPath", help='output path for summaries files')
    args = parser.parse_args()
    pd.set_option('display.max_columns', None)

    if not os.path.exists(args.controlledReleasesPath) or not os.path.exists(args.metPath):
        print('File not found')
        exit(1)
    idStart = args.controlledReleasesPath.index('_')  # find first underscore
    dateTime = args.controlledReleasesPath[idStart:-4]  # remove .csv
    met = dask.dataframe.read_csv(args.metPath)
    runPostProcessing(args.controlledReleasesPath, met, dateTime, args.outputPath)
