import argparse
import os

import Utils.TimeUtils as tu
import matplotlib.pyplot as plt
import pandas as pd
from Applications.METECControl.GUI.RefactoredWidgets.MET.WindroseScript import displayRose


def makeGraphs(epsumPath, expsumPath, metPath, outputFolder):

    epDF = pd.read_csv(epsumPath)
    expDF = pd.read_csv(expsumPath)
    metDF = pd.read_csv(metPath)

    # windorse for all experiments' average wind
    ws, wd = [], []
    for index, row in expDF.iterrows():
        ws.append(row['WindSpeedAvg'])
        wd.append(row['WindDirAvg'])
    displayRose("Avg wind per experiment", wd, ws, list(range(len(ws))))

    for index, row in expDF.iterrows():
        start = row['MainStartTimestamp']
        end = row['MainEndTimestamp']
        metIndexes = metDF.loc[(metDF['timestamp'] >= start) & (metDF['timestamp'] <= end)].index
        windSpeedData = metDF.loc[metIndexes, "MET-1.WS"].tolist()
        windDirData = metDF.loc[metIndexes, "MET-1.WD"].tolist()
        displayRose(str(int(row['ExperimentID'])), windDirData, windSpeedData, list(range(len(windDirData))))


    prePostTets = ['Pre Test', 'Post Test']
    # bfe histogram
    plt.figure(0)
    plt.xlabel("Best Flow Estimate Averages per Unique Release")
    plt.ylabel("Number of Unique Emission Purposes")
    plt.title("Histogram of Best Flow Estimates")
    bfeDF = epDF.loc[~epDF['EmissionCategory'].isin(prePostTets)]
    plt.hist(list(epDF['EPBFE']))
    plt.savefig(os.path.join(outputFolder, "UniqueReleaseHist.png"))

    # ep count histogram
    plt.figure(1)
    plt.title("Histogram of EP Count")
    plt.xlabel("Total Count of Emission Points in an Experiment")
    plt.ylabel("Number of Experiments")
    epCounts = expDF['EPCount']
    plt.hist(epCounts)
    plt.savefig(os.path.join(outputFolder, "EPCountHist.png"))

    # equipment group histogram
    plt.figure(2)
    plt.xlabel("Group ID")
    plt.ylabel("Number of Emission Points")
    plt.title("Histogram of Equipment Group ID")
    plt.hist(epDF['EquipmentGroupID'])
    plt.savefig(os.path.join(outputFolder, "EquipmentGroupHist.png"))

    # hist of durations
    plt.figure(3)
    plt.title("Histogram of Main Experiment Durations")
    plt.xlabel("Duration of Main Experiment (seconds)")
    plt.ylabel("Number of Experiments")
    dirs = []
    for index, row in expDF.iterrows():
        dirs.append(int(row['MainEndTimestamp'] - row['MainStartTimestamp']))
    plt.hist(dirs)
    plt.savefig(os.path.join(outputFolder, "DurationHist.png"))

    # wind dir average per experiment
    plt.figure(4)
    plt.xlabel("Degrees from North")
    plt.ylabel("Number of Experiments")
    plt.title("Histogram of Wind Direction Average")
    binRange = 15  # degrees
    plt.hist(expDF['WindDirAvg'], bins=range(0, 360+binRange, binRange))
    plt.savefig(os.path.join(outputFolder, "WindDirAvgHist.png"))

    plt.figure(5)
    plt.title("Histogram of Wind Speed Average")
    plt.ylabel("Number of Experiments")
    plt.xlabel("Average Wind Speed During an Experiment (m/s)")
    plt.hist(expDF['WindSpeedAvg'])
    plt.savefig(os.path.join(outputFolder, "WindSpeedAvgHist.png"))

    plt.figure(6)
    plt.title("Histogram of Temperature")
    plt.ylabel("Number of Experiments")
    plt.xlabel("Average Temperature (Celsius)")
    plt.hist(expDF['TAtmAvg'])
    plt.savefig(os.path.join(outputFolder, "TemperatureHist.png"))

    plt.figure(7)
    plt.title("Histogram of Experiment Start time")
    plt.ylabel("Number of Experiments")
    plt.xlabel("Start Time (Hour UTC)")
    startHours = [tu.EpochtoDT(ts, "UTC").hour for ts in expDF['StartTimestamp']]
    plt.hist(startHours)
    plt.savefig(os.path.join(outputFolder, "StartTimeHist.png"))



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(dest="EPSummary", help="Path to Emission Point Summary File")
    parser.add_argument(dest="ExperimentSummary", help="Path to Experiment Summary File")
    parser.add_argument(dest="met", help="Path to MET file.")
    parser.add_argument('-o', dest="outputPath", help='output path for graphs')
    args = parser.parse_args()

    if not os.path.exists(args.EPSummary) or not os.path.exists(args.met) or not os.path.exists(args.ExperimentSummary):
        print('File not found')
        exit(1)

    epsumPath = args.EPSummary
    expsumPath = args.ExperimentSummary
    metPath = args.met
    out = args.outputPath
    if out is None:
        out = os.path.split(args.EPSummary)[0]  # default folder

    # debug
    # epsumPath = 'UnitTests/EPSummary_unitTesting.csv'
    # expsumPath = 'UnitTests/ExperimentSummary_unitTesting.csv'
    # metPath = 'UnitTests/MET1hz_unitTesting.csv'

    makeGraphs(epsumPath, expsumPath, metPath, out)