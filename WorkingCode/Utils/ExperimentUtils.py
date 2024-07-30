import random
from hashlib import md5
import pandas as pd
import numpy as np

from Applications.METECControl.ExperimentDesigner.DesignerConfigs import TABLE_COLUMNS, ShorthandHelper
from Utils.FlowRateCalculator import calculateQg, orificeToCv
from Utils.Conversion import convert

REQUIRED_KEYS = ['Metadata', 'Experiment']
REQUIRED_METADATA_KEYS = ["FMConfig", "EPConfig", "EPMaxColumn", "Spans", "Pressures (psia)", "PreExperimentLength (sec)", "ExperimentLength (sec)", "PostExperimentLength (sec)", "ConfigValues"]
REQUIRED_EXPERIMENT_KEYS = ['Iterations', 'CloseAfterSection', 'CloseAfterIteration', 'ControlledReleases']

EXPECTED_TYPES = {
    "Metadata": {
        "FMConfig": {
            str: str
        },
        "EPConfig": {
            str: str
        },
        "Spans": {
            str: float
        },
        "Pressures (psia)": {
            str: float
        },
        "PreExperimentLength (sec)": int,
        "ExperimentLength (sec)": int,
        "PostExperimentLength (sec)": int,
        "ConfigValues": {
          "T1 (F)": float,
          "P2 (psia)": float,
          "SG": float,
          "K Rel N2": float
        }
    },
    "PreExperiment": {
        "CloseAfterSection": bool,
        "ControlledReleases": [
            {
                "Time": int,
                "Actions": [
                    {
                        "ActionType": str,
                        "EmissionPoint": str,
                        "FlowLevel": int,
                        "Controller": str,
                        "EmissionCategory": str,
                        "Intent": str,
                        "SetStates": {
                            str: int
                        }
                    }
                ]
            }
        ]
    },
    "Experiment": {
        "Iterations": int,
        "CloseAfterSection": bool,
        "CloseAfterIteration": bool,
        "ControlledReleases": [
            {
                "Time": int,
                "Actions": [
                    {
                        "ActionType": str,
                        "EmissionPoint": str,
                        "FlowLevel": int,
                        "Controller": str,
                        "EmissionCategory": str,
                        "Intent": str,
                        "SetStates": {
                            str: int
                        }
                    }
                ]
            }
        ]
    },
    "PostExperiment": {
        "CloseAfterSection": bool,
        "ControlledReleases": [
            {
                "Time": int,
                "Actions": [
                    {
                        "ActionType": str,
                        "EmissionPoint": str,
                        "FlowLevel": int,
                        "Controller": str,
                        "EmissionCategory": str,
                        "Intent": str,
                        "SetStates": {
                            str: int
                        }
                    }
                ]
            }
        ]
    }
}


class ExperimentParser:

    def __init__(self, script:dict):
        self.script = script
        self.metadata = script['Metadata']
        self.preExperiment = script.get("PreExperiment")
        self.experiment = script['Experiment']
        self.postExperiment = script.get("PostExperiment")

    def getEmissionPoints(self):
        return list(self.script['Metadata']['EPConfig'].keys())

    def getControlledReleases(self, experiment):
        """ experiment: either self.preExperiment, self.experiment, or self.postExperiment"""
        return experiment['ControlledReleases']

    def getIterations(self, experiment):
        if isinstance(experiment, dict):
            return experiment.get('Iterations', 1)
        return 1

    def isCloseAfterSection(self, experiment):
        if isinstance(experiment, dict):
            return experiment.get('CloseAfterSection', True)
        return True # todo: default to True or False?

    def isCloseAfterIter(self, experiment):
        if isinstance(experiment, dict):
            return experiment.get('CloseAfterIteration', True)
        return False # todo: default to True or False?


class MissingKeys(Exception):

    def __init__(self, typeOfKey, keys):
        Exception.__init__(self, f'Missing required {typeOfKey} keys: "{keys}"')


def verifyExperiment(expDict):
    missingKeys = [key for key in REQUIRED_KEYS if key not in expDict.keys()]
    if len(missingKeys) > 0:
        raise MissingKeys("first level", missingKeys)
    #metadata
    metadata = expDict.get("Metadata")
    missingKeys = [key for key in REQUIRED_METADATA_KEYS if key not in metadata.keys()]
    if len(missingKeys) > 0:
        raise MissingKeys("metadata", missingKeys)
    # if type(metadata.get('ExperimentLength (sec)')) is not int:
    #     raise TypeError('"ExperimentLength (sec)" should be type int')
    experiment = expDict.get("Experiment")
    missingKeys = [key for key in REQUIRED_EXPERIMENT_KEYS if key not in experiment.keys()]
    if len(missingKeys) > 0:
        raise MissingKeys("experiment", missingKeys)
    epsUsed = set()
    allReleases = list(experiment['ControlledReleases'])
    if expDict.get("PreExperiment"):
        allReleases += expDict['PreExperiment']['ControlledReleases']
    if expDict.get("PostExperiment"):
        allReleases += expDict['PostExperiment']['ControlledReleases']
    for release in allReleases:
        for action in release['Actions']:
            epsUsed.add(action['EmissionPoint'])
    fmCBs = set(metadata['FMConfig'].keys())
    pressureCBs = set(metadata['Pressures (psia)'].keys())
    spansCBs = set([cb[:cb.index('.')] for cb in metadata['Spans'].keys()])
    for ep in epsUsed:
        epshorthand = metadata['EPConfig'][ep]
        cb = 'CB-'+epshorthand[:epshorthand.index('-')]
        if cb not in fmCBs:
            raise Exception(f'Missing Flow Meter for control box "{cb}"')
        if cb not in pressureCBs:
            raise Exception(f'Missing Pressure for control box "{cb}')
        # if cb not in spansCBs:
        #     raise Exception(f'Missing span for control box "{cb}"')
    return True

# def viewExperimentGraph(experiment:dict):
#     df = experimentToDF(experiment)
#     x, total, ep, fm = calculateTableFlows(df)

def experimentToDF(experiment:dict):
    metadata = experiment['Metadata']
    releases = []
    pre = experiment.get("PreExperiment")
    if pre:
        prereleases = pre.get("ControlledReleases")
        for release in prereleases:
            release['Time'] -= metadata['PreExperimentLength (sec)']
        releases += prereleases
    releases += experiment['Experiment']['ControlledReleases']
    post = experiment.get("PostExperiment")
    if post:
        postreleases = post.get("ControlledReleases")
        for release in postreleases:
            release['Time'] += metadata['ExperimentLength (sec)']
        releases += postreleases
    df = controlledReleasesToDF(releases, metadata['EPConfig'], metadata['FMConfig'], metadata['Spans'], metadata['Pressures (psia)'])
    return df

def controlledReleasesToDF(releases, epConfig, fmConfig, spans, pressures, p2=12.5, t=70, sg=0.554):
    df = pd.DataFrame(columns=TABLE_COLUMNS)
    eID = 1
    for release in releases:
        time = release['Time']
        for action in release['Actions']:
            ep = action['EmissionPoint']
            level = action['FlowLevel']
            controller = action['Controller']
            pressure = pressures.get(controller)
            fm = fmConfig.get(controller)
            flowrate = 0
            for ev, state in action['SetStates'].items():
                if state == 0:  # on
                    orifice = controller+'.'+ev
                    flowrate += calculateQg(orificeToCv(spans.get(orifice)), pressure, p2, t, sg)
            shorthand = epConfig.get(ep)
            cb = ShorthandHelper(shorthand).cb
            df = pd.concat([df,pd.DataFrame({"Emission Point":ep,
                            "Flow Level": level,
                            "Timing": time,
                            "Flow Rate": flowrate,
                            "Link ID": "",
                            "Link Time": "",
                            "Flow Meter": fm,
                            "Total FM Flow": 0,
                            "Emission Category": action['EmissionCategory'],
                            "Intent": action["Intent"],
                            "Shorthand": shorthand,
                            "CB": cb
                            }, index=[eID])])
            eID+=1
    return df

def calculateTableFlows(df: pd.DataFrame) -> (np.array, np.array, dict, dict):
    """
    returns: x values array, totalFlows array, dictionary of ep flow arrays, dictionary of fm flow arrays
    """
    maxTime = df["Timing"].max()
    minTime = min(df['Timing'].min(), 0)
    graphRange = (maxTime-minTime+1)*2
    x = np.zeros(graphRange)
    uniqueEPS = df['Emission Point'].unique()
    uniqueFMS = df['Flow Meter'].unique()
    epFlows = {ep: np.zeros(graphRange) for ep in uniqueEPS}
    fmFlows = {fm: np.zeros(graphRange) for fm in uniqueFMS}
    totalFlows = np.zeros(graphRange)
    graphIndex = 0
    for time in range(minTime, maxTime+1):
        events = df.loc[df["Timing"] == time]
        for index, row in events.iterrows():
            # calculate flow from flow rate
            fr = row['Flow Rate']
            if fr == "":
                fr = 0
            epFlows[row['Emission Point']][graphIndex:] = fr
        totalFlowAtTime = sum([flow[graphIndex] for flow in epFlows.values()])
        totalFlows[graphIndex] = totalFlowAtTime
        totalFlows[graphIndex+1] = totalFlowAtTime
        x[graphIndex] = time
        x[graphIndex+1] = time+1
        graphIndex += 2
    for fm in uniqueFMS:
        includedEPs = df.loc[df['Flow Meter'] == fm, "Emission Point"].unique()
        for ep in includedEPs:
            fmFlows[fm] += epFlows[ep]
    return x, totalFlows, epFlows, fmFlows


def epToColor(ep):
    # random.seed(hash(ep) % 1000)
    random.seed(int(md5(str.encode(ep)).hexdigest(), 16))
    r = random.randint(100, 255)
    g = random.randint(100, 255)
    b = random.randint(100, 255)
    return r,g,b


if __name__ == '__main__':
    # verifyExperiment({"Metadata":{"FMConfig": {}, "EPConfig":{}, "Spans":{}, "Pressures (psia)":{}, "PreExperimentLength (sec)":1, "ExperimentLength (sec)":"", "PostExperimentLength (sec)":1}, "Experiment":{}})
    # verifyExperiment({"Metadata": {"FMConfig": {}, "EPConfig": {}, "Spans": {}, "Pressures (psia)": {},
    #                                "PreExperimentLength (sec)": 1, "ExperimentLength (sec)": "",
    #                                "PostExperimentLength (sec)": 1}, "Experiment":
    #     {"Iterations": 1, "CloseAfterSection": True, "CloseAfterIteration": True, "ControlledReleases":[]}})
    expDict = {
      "Metadata": {
        "FMConfig": {
          "CB-1W": "GSH-1.FM-2",
          "CB-2S": "GSH-1.FM-4"
        },
        "EPConfig": {
          "1W-11": "1W-1A-R",
          "2S-18": "2S-3B"
        },
        "Spans": {
          "CB-1W.EV-14": 0.0,
          "CB-1W.EV-24": 0.0,
          "CB-1W.EV-34": 0.0,
          "CB-1W.EV-11": 0.0071,
          "CB-1W.EV-12": 0.0102,
          "CB-1W.EV-21": 0.0102,
          "CB-1W.EV-31": 0.0122,
          "CB-1W.EV-13": 0.015,
          "CB-1W.EV-22": 0.015,
          "CB-1W.EV-32": 0.019,
          "CB-1W.EV-23": 0.021,
          "CB-1W.EV-33": 0.025,
          "CB-2S.EV-14": 0.0,
          "CB-2S.EV-24": 0.0,
          "CB-2S.EV-34": 0.0,
          "CB-2S.EV-11": 0.0071,
          "CB-2S.EV-12": 0.0102,
          "CB-2S.EV-21": 0.0102,
          "CB-2S.EV-31": 0.0122,
          "CB-2S.EV-13": 0.015,
          "CB-2S.EV-22": 0.015,
          "CB-2S.EV-32": 0.019,
          "CB-2S.EV-23": 0.021,
          "CB-2S.EV-33": 0.025,
          "GSH-1.FM-2": 100.0,
          "GSH-1.FM-4": 100.0
        },
        "Pressures (psia)": {
          "CB-1W": 80,
          "CB-2S": 80
        },
        "EPStats": {
          "1W-11": {
            "max flow rate (SLPM)": 14.1,
            "avg flow rate (SLPM)": 12.230999999999998,
            "percentEmitting": 1.0
          },
          "2S-18": {
            "max flow rate (SLPM)": 12.95,
            "avg flow rate (SLPM)": 6.475,
            "percentEmitting": 0.5
          }
        },
        "PreExperimentLength (sec)": 721,
        "ExperimentLength (sec)": 10,
        "PostExperimentLength (sec)": 660,
        "Config Values": {
          "T1 (F)": 70.0,
          "P2 (psia)": 12.5,
          "SG": 0.554,
          "K Rel N2": 0.75
        }
      },
      "PreExperiment": {
        "CloseAfterSection": True,
        "ControlledReleases": [
          {
            "Time": 0,
            "Actions": [
              {
                "ActionType": "Defined",
                "EmissionPoint": "2S-18",
                "FlowLevel": 1,
                "Controller": "CB-2S",
                "EmissionCategory": "Pre Test",
                "Intent": "",
                "SetStates": {
                  "EV-31": 0,
                  "EV-32": 1,
                  "EV-33": 1,
                  "EV-34": 0
                }
              }
            ]
          }
        ]
      },
      "Experiment": {
        "Iterations": 1,
        "CloseAfterSection": False,
        "CloseAfterIteration": True,
        "ControlledReleases": [
          {
            "Time": 0,
            "Actions": [
              {
                "ActionType": "Defined",
                "EmissionPoint": "1W-11",
                "FlowLevel": 1,
                "Controller": "CB-1W",
                "EmissionCategory": "Fugitive",
                "Intent": "",
                "SetStates": {
                  "EV-11": 0,
                  "EV-12": 1,
                  "EV-13": 1,
                  "EV-14": 1
                }
              }
            ]
          }
        ]
      },
      "PostExperiment": {
        "CloseAfterSection": True,
        "ControlledReleases": [
          {
            "Time": 0,
            "Actions": [
              {
                "ActionType": "Defined",
                "EmissionPoint": "2S-18",
                "FlowLevel": 1,
                "Controller": "CB-2S",
                "EmissionCategory": "Post Test",
                "Intent": "",
                "SetStates": {
                  "EV-31": 0,
                  "EV-32": 1,
                  "EV-33": 1,
                  "EV-34": 0
                }
              }
            ]
          }
        ]
      }
    }
    verifyExperiment(expDict)
    df = controlledReleasesToDF(expDict['Experiment']['ControlledReleases'], expDict['Metadata']['EPConfig'], expDict['Metadata']['FMConfig'], expDict['Metadata']['Spans'],expDict['Metadata']['Pressures (psia)'])
    print(calculateTableFlows(df))