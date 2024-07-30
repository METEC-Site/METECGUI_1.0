from enum import Enum

from PyQt5 import QtCore as qtc

TABLE_COLUMNS = ["Emission Point", "Flow Level", "Timing", "Flow Rate", "Link ID", "Link Time", "Flow Meter", "Total FM Flow", "Emission Category", "Intent", "Shorthand", 'CB', 'Row']

EP_COLUMNS = ["Emission Point", "Shorthand", "EV", "Description", 'CB']
FM_COLUMNS = ["Controller", "Flowmeter ID"]
SPANS_COLUMNS = ["Flow Name", "Orifice"]
PRESSURE_COLUMNS = ['Controller', 'Pressure (psia)']


class EmissionCategories(Enum):
    Fugitive = "Fugitive"
    Vent = "Vent"
    PreTest = "Pre Test"
    PostTest = "Post Test"


def getEmissionCategory(value):
    for cat in EmissionCategories:
        if cat.value == value:
            return cat


class EPColumns(Enum):
    EmissionPoint = "Emission Point"
    Shorthand = "Shorthand"
    EV = "EV"
    Description = "Description"

class FMColumns(Enum):
    Controller = "Controller"
    FlowmeterID = "Flowmeter ID"


class DesignerConfigManager:
    fmChanged = qtc.pyqtSignal()
    epChanged = qtc.pyqtSignal()
    spansChanged = qtc.pyqtSignal()
    pressuresChanged = qtc.pyqtSignal()

    def __init__(self):
        self.ep = None
        self.fm = None
        self.spans = None
        self.pressures = None

    def setEP(self, df):
        self.ep = df

    def setFM(self, df):
        self.fm = df

    def setSpans(self, df):
        self.spans = df

    def setPressures(self, df):
        self.pressures = df

    def getShorthand(self, epID):
        return self.ep.loc[self.ep['Emission Point'] == epID, 'Shorthand'].item()

    def getCBFromEP(self, epID):
        return self.ep.loc[self.ep['Emission Point'] == epID, 'CB'].item()

    def getFMFromEP(self, epID):
        controller = self.getCBFromEP(epID)
        return self.fm.loc[self.fm['Controller'] == controller, "Flowmeter ID"].item()


class ShorthandHelper:  # helper class

    def __init__(self, shorthand):
        split = shorthand.split("-")
        self.pad = split[0][0]
        self.controller = split[0][1:]
        self.cb = "CB-"+self.pad+self.controller
        self.row = split[1][0]
        self.evState = split[1][1]
        self.mvState = None
        if len(split) == 3:
            self.mvState = split[2][0]