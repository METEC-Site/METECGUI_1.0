import unittest

import Applications.METECControl.GUI.CustomWidgets as cw
from Applications.METECControl.GUI.GUIInterface import GUIInterface
from Applications.METECControl.GUI.METECWidgets import SidebarCommandWidget as sb
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets import TemperatureGauge as tg, Valve, \
    PressureGauge as pg, ControlPanel as cp, UnitOutputBox as uob
from Applications.METECControl.GUI.RefactoredWidgets.Test.TestContainer import TestContainer
from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses.Commands import CommandMethod
from Framework.Manager.DataManager import DataManager
from Framework.Manager.EventManager import EventManager
from PyQt5 import QtCore as qtc
from Utils import Conversion
from Utils import QtUtils as qu


class GUITestInterface():

    def __init__(self, ID="MainTestGUI", **kwargs):
        self.app = qu.getApp()
        self.updateTimer = qtc.QTimer()
        self.updateTimer.timeout.connect(self.update)
        self.updateTimer.setSingleShot(True)
        self.subWidgets = {}
        self.widgetConfig = {}

    def getWidgetFromName(self, widgetName):
        return self.subWidgets.get(widgetName, None)

    def update(self):
        for widgetName, widgetObj in self.subWidgets.items():
            widgetObj.update()
        self.updateTimer.start(1000)

    @CommandMethod
    def getSourceInfo(self, commandDest, args=[], kwargs={}):
        return {}

    @CommandMethod
    def shutdown(self):
        pass


class TestGuiManager(unittest.TestCase):

    def testGUIInterface(self):
        archiver = DirectoryArchiver(readonly=True, baseDir="./")
        dm = DataManager(archiver)
        em = EventManager(archiver)
        guiinterface = GUIInterface(archiver, None, dm, em, configChannels=[])
        return guiinterface

    def testTestContainer(self):
        gi = self.testGUIInterface()
        tl = TestContainer(gi, "testcontainer", None)
        tl.fileSelectWidget.textBox.setText("./")
        tl.fileSelectWidget.selectFileButton.click()
        tl.loadingWidget.runButton.click()


    def testFakeGUIManager(self):
        fakeGuiManager = GUITestInterface()
        pGauge = pg.PressureGauge(fakeGuiManager, "foo buddy")

    def testPressureGaugeChangeVal(self):
        fakeGuiManager = GUITestInterface()
        pGauge = pg.PressureGauge(fakeGuiManager, "foo buddy")
        pGauge.changeValue(10.01)
        self.assertEqual(pGauge.corrValue, 10.01)
        self.assertEqual(Conversion.convert(pGauge.corrValue, pGauge.inputUnit, pGauge.corrOutputUnit),
                         pGauge.displayGauge.displayValue, float(pGauge.unitBox.valueBox.text()))

    def testPressureGaugeChangeUnit(self):
        fakeGuiManager = GUITestInterface()
        pGauge = pg.PressureGauge(fakeGuiManager, "foo buddy")
        pGauge.changeValue(20.01)
        pGauge.changeUnit("PSIG")
        self.assertEqual(pGauge.corrValue, 20.01)
        self.assertEqual(pGauge.corrOutputUnit, "PSIG")
        self.assertEqual(Conversion.convert(pGauge.corrValue, pGauge.inputUnit, pGauge.corrOutputUnit),
                         pGauge.displayGauge.displayValue, float(pGauge.unitBox.valueBox.text()))


    def testPressureGaugeChangeMinMax(self):
        fakeGuiManager = GUITestInterface()
        pGauge = pg.PressureGauge(fakeGuiManager, "foo buddy")
        pGauge.changeValue(10)
        pGauge.changeMinMax(0, 100, pGauge.inputUnit)
        self.assertEqual(pGauge.corrValue, 10)
        self.assertEqual(Conversion.convert(pGauge.corrValue, pGauge.inputUnit, pGauge.corrOutputUnit),
                         pGauge.displayGauge.displayValue, float(pGauge.unitBox.valueBox.text()))

    def testTemperatureGauge(self):
        fakeGuiManager = GUITestInterface()
        tGauge = tg.TemperatureGauge(fakeGuiManager, "foo")

    def testTemperatureGaugeChangeValue(self):
        fakeGuiManager = GUITestInterface()
        tGauge = tg.TemperatureGauge(fakeGuiManager, "foo")
        tGauge.changeValue(10.01)
        self.assertEqual(tGauge.corrValue, 10.01)
        self.assertEqual(Conversion.convert(tGauge.corrValue, tGauge.inputUnit, tGauge.corrOutputUnit),
                         tGauge.displayGauge.displayValue, float(tGauge.unitBox.valueBox.text()))

    def testTemperatureGaugeChangeUnit(self):
        fakeGuiManager = GUITestInterface()
        tGauge = tg.TemperatureGauge(fakeGuiManager, "foo")
        tGauge.changeValue(10)
        tGauge.changeUnit("C")
        self.assertEqual("C", tGauge.displayGauge.corrOutputUnit)
        self.assertEqual("C", tGauge.unitBox.getDisplayUnit())
        self.assertEqual(10, tGauge.corrValue)
        self.assertEqual(Conversion.convert(tGauge.corrValue, tGauge.inputUnit, tGauge.corrOutputUnit),
                         tGauge.displayGauge.displayValue, float(tGauge.unitBox.valueBox.text()))

    def testValve(self):
        fakeGuiManager = GUITestInterface()
        v = Valve.Valve(fakeGuiManager, "foo")

    def testSideBar(self):
        fakeGuiManager = GUITestInterface()
        s = sb.SidebarCommand(fakeGuiManager, "foo")

    def testUnitOutputBox(self):
        fakeGuiManager = GUITestInterface()
        w = uob.UnitOutputBox(fakeGuiManager, "foo")
        w.changeUnit("C")

    def testMinMaxDialog(self):
        w = cw.MinMaxDialogBox.MinMaxDialog(None, "F", "F", 0, 100)

    def testControlPanel(self):
        fakeGuiManager = GUITestInterface()
        w = cp.ControlPanel(fakeGuiManager, "foo")
        w.setConStatus(True)
        self.assertEqual("True", w.connectedStatus.conValue)
        w.setConStatus(False)
        self.assertEqual("False", w.connectedStatus.conValue)

