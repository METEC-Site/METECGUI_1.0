import os
import sys
import unittest

from Applications.METECControl.ExperimentDesigner.ExperimentDesigner import ExperimentDesigner
from PyQt5 import QtWidgets as qtw
from Utils.ExperimentUtils import verifyExperiment

app = qtw.QApplication(sys.argv)


class TestDesigner(unittest.TestCase):
    sys.argv = ['TestExperimentDesigner.py', '-d']
    ed = ExperimentDesigner()

    def testAddEvent(self):
        ep = "1W-11"
        fm = self.ed.actionsConfigWidget.getFMfromEP(ep)
        addOne = self.ed.actionsConfigWidget.addEPEvent("1W-11", 1, 1, fm, "test")
        self.assertEqual(addOne, 1)
        df = self.ed.actionsConfigWidget.getActions()
        self.assertEqual(len(df), 1)


class TestPresets(unittest.TestCase):
    ed = ExperimentDesigner()

    def testStairstep(self):
        self.ed.actionsConfigWidget.preset_stair.setSelectedEP("1W-11")
        self.ed.actionsConfigWidget.preset_stair.numberOfStepsWidget.setValue(7)
        self.ed.actionsConfigWidget.preset_stair.addButton.click()
        df = self.ed.actionsConfigWidget.getActions()
        self.assertEqual(list(range(1,8)), list(df['Flow Level']))


class TestCalEvents(unittest.TestCase):
    ed = ExperimentDesigner()

    def testAutoCalPeriod(self):
        ep = "1W-11"
        fm = self.ed.actionsConfigWidget.getFMfromEP(ep)
        addOne = self.ed.actionsConfigWidget.addEPEvent("1W-11", 1, 1, fm, "")
        self.ed.calMenuWidget.check_preCalPeriod.setChecked(True)
        self.ed.calMenuWidget.check_postCalPeriod.setChecked(True)
        self.ed.updateCalPeriods()
        df = self.ed.actionsConfigWidget.getActions()
        self.assertEqual(df.loc[1, 'Timing'], 1)
        self.assertEqual(df.loc[2, 'Timing'], -241)
        self.assertEqual(df.loc[3, 'Timing'], 2)
        self.assertEqual(df.loc[4, 'Timing'], -61)
        self.assertEqual(df.loc[5, 'Timing'], 182)
        self.assertEqual(df.loc[1, 'Flow Level'], 1)
        self.assertEqual(df.loc[2, 'Flow Level'], 1)
        self.assertEqual(df.loc[3, 'Flow Level'], 1)
        self.assertEqual(df.loc[4, 'Flow Level'], 0)
        self.assertEqual(df.loc[5, 'Flow Level'], 0)


class TestSavingExperiments(unittest.TestCase):
    ed = ExperimentDesigner()

    def testloadConfigs(self):
        self.ed.loadConfigs(os.path.abspath('../ExampleExperiments/example configs'))

    def testloadTable(self):
        self.ed.actionsConfigWidget.loadTable(os.path.abspath('../ExampleExperiments/exampleTable.csv'))

    def testadd(self):
        ep = "1W-11"
        fm = self.ed.actionsConfigWidget.getFMfromEP(ep)
        addOne = self.ed.actionsConfigWidget.addEPEvent("1W-11", 1, 1, fm, "test")

    def testSaveExperiment(self):
        ep = "1W-11"
        fm = self.ed.actionsConfigWidget.getFMfromEP(ep)
        addOne = self.ed.actionsConfigWidget.addEPEvent("1W-11", 1, 1, fm, "test")
        d = self.ed.getExperimentDict()
        self.assertTrue(verifyExperiment(d))

if __name__ == '__main__':
    unittest.main()
