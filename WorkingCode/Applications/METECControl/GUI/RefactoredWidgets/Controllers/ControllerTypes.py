from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.AdhocController import AdhocController
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.Controller import Controller
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.PressureGauge import PressureGauge
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.TemperatureGauge import TemperatureGauge
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.Valve import Valve
from PyQt5 import QtCore as qtc
from PyQt5.QtCore import QTimer


# todo: use the sensor properties obtained from controller!
class GSHController(Controller):
    def __init__(self, GUIInterface, name=None, parent=None, processGroups=None, controllerName=None, *args, **kwargs):
        Controller.__init__(self, GUIInterface=GUIInterface, name=name, controllerName=controllerName, parent=parent, processGroups=processGroups,
                            *args, **kwargs)
        self.gasHouse = int(controllerName[controllerName.index("-")+1:])
        self.currentExperimentID = None
        self.lockCheckTimer = QTimer()
        self.lockCheckTimer.timeout.connect(self.updateCurrentExperimentTimer)
        self.updateCurrentExperimentTimer()

    def updateCurrentExperimentTimer(self):
        name, experiment = self.GUIInterface.checkGSHLock(self.gasHouse)
        if self.currentExperimentID != experiment:
            if experiment is not None:
                if self.currentExperimentID != experiment: # new experiment we didn't know about
                    self.adhoc.setExperimentID(experiment)
                    if name == self.ctrlName:
                        print("My adhoc experiment, unlock valves:", self.ctrlName)
                        ...  # lock valves
                    else:
                        print("Automated experiment, lock valves:", self.ctrlName)
                        ...  # unlock valves
            else:
                self.currentExperimentID = None
                print("Experiment ended, unlock valves:", self.ctrlName)
                ...  # unlock valves
        self.currentExperimentID = experiment

        self.lockCheckTimer.start(1000)

    def buildAdhocController(self, gasHouseNumber):
        self.adhoc = AdhocController(self.GUIInterface, gasHouse=gasHouseNumber, controllerName=self.ctrlName)
        self.layout().addWidget(self.adhoc, 1, 1)

    def _buildValves(self):
        evLabel = "EV-1"
        valveName = f"{self.ctrlName}.{evLabel}"
        widget = Valve(GUIInterface=self.GUIInterface, name=valveName, label=evLabel, parent=self, eventSource=self.corrSource,
                         sensorProperties=self.sensorProperties.get(valveName, {}))
        self.outputWidgets[valveName] = widget
        self.inletValveLayout.addWidget(widget, 1, 1, 1, 1, qtc.Qt.AlignVCenter)

    def _buildPTs(self):
        # todo: do the same corrInputMax/min for other sensors in the gas houses.
        pt1Label = "PT-1"
        pt1Name = f"{self.ctrlName}.{pt1Label}"
        pt1Props = self.sensorProperties.get(pt1Name, {})
        widget1 = PressureGauge(self.GUIInterface, name=pt1Name, label=pt1Label, parent=self, corrInputMax=pt1Props.get("max", 150))

        pt2Label = "PT-2"
        pt2Name = f"{self.ctrlName}.{pt2Label}"
        pt2Props = self.sensorProperties.get(pt2Name, {})
        widget2 = PressureGauge(self.GUIInterface, name=pt2Name, label=pt2Label, parent=self, corrInputMax=pt2Props.get("max", 150))

        self.outputWidgets[pt1Name] = widget1
        self.outputWidgets[pt2Name] = widget2
        self.ptLayout.addWidget(widget1)
        self.ptLayout.addWidget(widget2)

    def _buildTCs(self):
        tc1Label = "TC-1"
        tc1Name = f"{self.ctrlName}.{tc1Label}"
        widget1 = TemperatureGauge(self.GUIInterface, name=tc1Name, parent=self,
                                  sensorProperties=self.sensorProperties.get(tc1Name, {}))

        tc2Label = "TC-2"
        tc2Name = f"{self.ctrlName}.{tc2Label}"
        widget2 = TemperatureGauge(self.GUIInterface, name=tc2Name, parent=self,
                                  sensorProperties=self.sensorProperties.get(tc2Name, {}))

        self.outputWidgets[tc1Name] = widget1
        self.outputWidgets[tc2Name] = widget2
        self.tcLayout.addWidget(widget1)
        self.tcLayout.addWidget(widget2)


class FourByThree(Controller):
    def __init__(self, GUIInterface, name=None, parent=None, processGroups=None, controllerName=None, *args, **kwargs):
        Controller.__init__(self, GUIInterface=GUIInterface, name=name, controllerName=controllerName, parent=parent, processGroups=processGroups,
                            *args, **kwargs)

    def _buildValves(self):
        for i in range(1, 4):  # rows 1-3
            for j in range(1, 5):  # columns 1-4
                label = f"EV-{i}{j}"
                sensorName = f"{self.ctrlName}.{label}"
                widget = Valve(GUIInterface=self.GUIInterface, name=sensorName, label=label, eventSource=self.corrSource,
                               parent=self, sensorProperties=self.sensorProperties.get(sensorName, {}))
                self.outputWidgets[sensorName] = widget
                self.valveManifoldLayout.addWidget(widget, i, j, 1, 1)

    def _buildPTs(self):
        ptLabel = "PT-1"
        ptName = f"{self.ctrlName}.{ptLabel}"
        widget = PressureGauge(self.GUIInterface, name=ptName, label=ptLabel, parent=self,
                                sensorProperties=self.sensorProperties.get(ptName, {}))
        self.outputWidgets[ptName] = widget
        self.ptLayout.addWidget(widget)

    def _buildTCs(self):
        tcLabel = "TC-1"
        tcName = f"{self.ctrlName}.{tcLabel}"
        widget = TemperatureGauge(self.GUIInterface, name=tcName, parent=self,
                                  sensorProperties=self.sensorProperties.get(tcName, {}))
        self.outputWidgets[tcName] = widget
        self.tcLayout.addWidget(widget)

class FiveByTwo(Controller):
    def __init__(self, GUIInterface, name=None, parent=None, processGroups=None, controllerName=None, *args, **kwargs):
        Controller.__init__(self, GUIInterface=GUIInterface, name=name, controllerName=controllerName, parent=parent,
                            processGroups=processGroups, *args, **kwargs)

    def _buildValves(self):
        for i in range(1, 3): # rows 1-2
            for j in range(1,6): # columns 1-5
                label = f"EV-{i}{j}"
                sensorName = f"{self.ctrlName}.{label}"
                widget = Valve(GUIInterface=self.GUIInterface, name=sensorName, label=label, eventSource=self.corrSource,
                                                       parent=self, sensorProperties=self.sensorProperties.get(sensorName, {}))
                self.outputWidgets[sensorName] = widget
                self.valveManifoldLayout.addWidget(widget, i, j, 1, 1)

    def _buildPTs(self):
        ptLabel = "PT-1"
        ptName = f"{self.ctrlName}.{ptLabel}"
        widget = PressureGauge(self.GUIInterface, name=ptName, label=ptLabel, parent=self,
                               sensorProperties=self.sensorProperties.get(ptName, {}))
        self.outputWidgets[ptName] = widget
        self.ptLayout.addWidget(widget)

    def _buildTCs(self):
        tcLabel = "TC-1"
        tcName = f"{self.ctrlName}.{tcLabel}"
        widget = TemperatureGauge(self.GUIInterface, name=tcName, parent=self,
                                   sensorProperties=self.sensorProperties.get(tcName, {}))
        self.outputWidgets[tcName] = widget
        self.tcLayout.addWidget(widget)

class GMRController(Controller):
    def __init__(self, GUIInterface, name=None, parent=None, processGroups=None, controllerName=None, *args, **kwargs):
        Controller.__init__(self, GUIInterface=GUIInterface, name=name, controllerName=controllerName, parent=parent,
                            processGroups=processGroups, *args, **kwargs)

    def _buildValves(self):
        pass

    def _buildPTs(self):
        pass

    def _buildTCs(self):
        pass
