import pathlib
import random

import Utils.TimeUtils as tu
import pandas as pd

exampleFieldSpecs = {
    "field1": {
        "default": 0,
        "min": 0,
        "max": 1,
        "noise": .1, # max amount of noise allowed on the field. 0 to disable.
        "type": int, # (int, float) allowed
        "profile": "default" # can be "default" for consistent or "rand" for random numbers between min and max.
    }
}

def genTimestamps(startTimestamp, duration=86400, hz=1, tsNoise=None):
    """
    startTimestamp: UTC timestamp (float) which starts the series
    duration: duration (in seconds) of the
    hz: number of timestamps that should be generated per second
    tsNoise:

    return: a list of timestamps (monotonically increasing) starting at start timestamp
    """
    if tsNoise is None:
        tsNoise = 0
    if hz <= 0:
        raise ValueError(f"hz argument must be greater than 0.")

    timestamps = [startTimestamp]
    while timestamps[-1] - timestamps[0] <= duration:
        jitter = random.uniform(-1*tsNoise, tsNoise)
        interval = 1/hz
        timestamps.append(timestamps[-1]+interval+jitter)
    return timestamps



def makeDataset(fieldSpecs, hz, startTimestamp, duration=86400, tsNoise=None, setpoints=None):
    """
    filename: output filepath where this dataset should be written.
    """
    dataset = {}
    timestamps = genTimestamps(startTimestamp, duration, hz, tsNoise)
    dataset['timestamp'] = timestamps

    for fieldName, fieldInfo in fieldSpecs.items():
        fieldDefault = fieldInfo.get("default", 0)
        fieldMin = fieldInfo.get("min", 0)
        fieldMax = fieldInfo.get("max", 1)
        fieldNoise = fieldInfo.get('noise', 0)
        fieldType = fieldInfo.get('type', float)
        profile = fieldInfo.get('profile', "default")

        fieldSetpts = setpoints[fieldName] if setpoints and fieldName in setpoints else {tu.MIN_EPOCH:fieldDefault}
        sortedSetpts = {k: fieldSetpts[k] for k in sorted(fieldSetpts.keys())}
        setptTimestamps = list(sorted(sortedSetpts.keys()))
        if profile == "default":
            # initialize dataset to be the default (plus jitter/noise if specified)
            fieldData = [fieldType(fieldDefault + random.uniform(-1*fieldNoise, fieldNoise)) for i in dataset['timestamp']]

            # initialize the current/next timestamp and the current setpoint.
            curSetpt = fieldDefault
            nextTS = setptTimestamps[0] if len(setptTimestamps) > 0 else tu.MAX_EPOCH

            # iterate through the field dataset, adding data with jitter to the list of data values based on setpoints.
            for i in range(0, len(timestamps)):
                ts = timestamps[i]
                if nextTS-ts <= 0 and len(setptTimestamps) > 0:
                    # if time has come to change setpoints, update setpt and timestamps.
                    curTS = setptTimestamps[0]
                    setptTimestamps.remove(curTS)
                    curSetpt = sortedSetpts.pop(curTS)
                    nextTS = setptTimestamps[0] if len(setptTimestamps) > 0 else tu.MAX_EPOCH
                # set the value of the field
                fieldData[i] = fieldType(curSetpt + random.uniform(-1*fieldNoise, fieldNoise))
        elif profile == "rand":
            fieldData = [fieldType(random.uniform(fieldMin, fieldMax)) for i in dataset['timestamp']]
        else:
            raise ValueError(f'Expecting profile for field {fieldName} to be either "rand" or "default", got "{profile}" instead')

        dataset[fieldName] = fieldData
    return dataset

if __name__ == '__main__':

    dataSetpts = {
        "GSH-1.LJ-1":{
            "GSH-1.EV-1": {10: 0},
            "GSH-1.FM-1": {30: 4, 120:3, 300:2},
            "GSH-1.FM-2": {10:1, 20:2, 30:3, 40:4, 50:5},
            "GSH-1.FM-3": {20: 10, 10000: 20}
        }
    }

    GSH1data = makeDataset(fieldSpecs=fieldSetup["GSH-1.LJ-1"], hz=1, startTimestamp=0, duration=100, tsNoise=.01, setpoints=dataSetpts["GSH-1.LJ-1"])
    GSH1df = pd.DataFrame(data=GSH1data)
    GSH1df.to_csv(pathlib.Path(pathlib.Path(__file__).parent).joinpath("ExampleOutput.csv"))
