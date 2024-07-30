import math

import numpy as np
import pandas as pd

orificeList = np.asarray([0, 0.004, 0.005, 0.006, 0.007, 0.008, 0.009, 0.01, 0.011, 0.012, 0.013, 0.014, 0.015, 0.016, 0.017, 0.018, 0.019, 0.02, 0.021, 0.022, 0.023, 0.024, 0.025, 0.026, 0.027, 0.028, 0.029, 0.031, 0.032, 0.033, 0.035, 0.037, 0.038, 0.039, 0.04, 0.041, 0.042, 0.043, 0.047, 0.052, 0.055, 0.06, 0.063, 0.067, 0.07, 0.073, 0.076, 0.079, 0.081, 0.086, 0.089, 0.094, 0.096, 0.1, 0.104, 0.109, 0.113, 0.12, 0.125])
cvList = np.asarray([0, 0.00035, 0.00061, 0.00086, 0.0012, 0.0015, 0.0019, 0.0025, 0.0028, 0.0034, 0.0038, 0.0043, 0.005, 0.0055, 0.0067, 0.0073, 0.008, 0.0088, 0.0096, 0.011, 0.012, 0.013, 0.014, 0.016, 0.017, 0.018, 0.019, 0.022, 0.024, 0.025, 0.028, 0.031, 0.032, 0.033, 0.036, 0.038, 0.039, 0.041, 0.048, 0.059, 0.068, 0.081, 0.088, 0.1, 0.11, 0.12, 0.13, 0.14, 0.15, 0.17, 0.18, 0.2, 0.21, 0.23, 0.25, 0.27, 0.31, 0.34, 0.37])


def orificeToCv(orificeSize):
    index = (np.abs(orificeList - orificeSize)).argmin()
    if orificeSize != orificeList[index]:
        print(f"Orifice size: {orificeSize} not found in list. Using Cv for {orificeList[index]} instead.")
    return cvList[index]


def calculateQg(cv, p1, p2=12.5, t=70, sg=0.544):
    """
    Returns flowrate in SCFH based on critical and subcritical flow calculation
    Refer to: SVN MONITOR\trunk\Design Input\Flow Component Data Sheets\Flow-Calculation-for-Gases.pdf
    cv: coefficient of flow
    p1: pressure recorded at the valve
    p2: atmospheric pressure
    t: degrees F
    sg: specific gravity of medium. 0.544 for methane in 70
    """
    if p1 < p2:
        return 0
    t = t+460  # convert from F to R
    if p1 < 2 * p2:  # sub-critical flow
        return 962*cv*math.sqrt((p1**2-p2**2)/(sg*t))
    else:
        return cv*816*p1/math.sqrt(sg*t)


def getValveColumns(flowlevel):
    columns = []
    if flowlevel & 1:
        columns.append(1)
    if flowlevel & 2:
        columns.append(2)
    if flowlevel & 4:
        columns.append(3)
    if flowlevel & 8:
        columns.append(4)
    return columns


def compareKeyValueDataFrames(df1:pd.DataFrame, df2:pd.DataFrame):
    """ assert column 1 is the same for df1 and df2"""
    df1.columns = ['a', 'b']
    df2.columns = ['a', 'b']
    errorRows = []
    for index, row in df1.iterrows():
        val1 = row['b']
        val2 = df2.loc[df2['a'] == row['a'], 'b'].item()
        print(val1, val2, val1 == val2)
        if val1 != val2:
            errorRows.append(index)
    return errorRows
