import pyqtgraph
from Applications.METECControl.GUI.RefactoredWidgets.Controllers.GSHS import GSH1
from Applications.METECControl.GUI.RefactoredWidgets.Controllers.Pad1 import CB1W, CB1S, CB1T
from Applications.METECControl.GUI.RefactoredWidgets.Controllers.Pad2 import CB2W, CB2S, CB2T
from Applications.METECControl.GUI.RefactoredWidgets.Graphs.BasicGraph import BasicGraph
from Framework.BaseClasses.QtMixin import QtMixin
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
from PyQt5 import QtWidgets as qtw


class GSH1Tab(qtw.QWidget, QtMixin):

    def __init__(self, GUIInterface, name=None, parent=None):
        QtMixin.__init__(self, GUIInterface, name=name, parent=parent)
        qtw.QWidget.__init__(self, parent=parent)
        self.layout = qtw.QGridLayout()
        self.setLayout(self.layout)

        self.buildGUI()

    def buildGUI(self):
        self.controllerGSH1 = GSH1(self.GUIInterface, "GSH-1 Control", controllerName='GSH-1', parent=self, processGroups=["PAD-1", "PAD-2"])
        self.layout.addWidget(self.controllerGSH1, 0, 0)
        self.graphGSH1 = BasicGraph(self.GUIInterface, "GSH-1 Graph",  controllerName="GSH-1", parent=self, label="GSH-1")
        self.layout.addWidget(self.graphGSH1, 0, 1, 1, 2)

        FM1Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.red), width=1)
        self.graphGSH1.addCurveItem(name='GSH-1.FM-1', label="FM-1",
                                    corrSource="GSH-1.LJ-1_corr", corrField="GSH-1.FM-1", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH1.sensorProperties, pen=FM1Pen)
        FM2Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.yellow), width=1)
        self.graphGSH1.addCurveItem(name='GSH-1.FM-2', label="FM-2",
                                    corrSource="GSH-1.LJ-1_corr", corrField="GSH-1.FM-2", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH1.sensorProperties, pen=FM2Pen)
        FM3Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.white), width=1)
        self.graphGSH1.addCurveItem(name='GSH-1.FM-3', label="FM-3",
                                    corrSource="GSH-1.LJ-1_corr", corrField="GSH-1.FM-3", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH1.sensorProperties, pen=FM3Pen)
        FM4Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.gray), width=1)
        self.graphGSH1.addCurveItem(name='GSH-1.FM-4', label="FM-4",
                                    corrSource="GSH-1.LJ-1_corr", corrField="GSH-1.FM-4", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH1.sensorProperties, pen=FM4Pen)
        FM5Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.cyan), width=1)
        self.graphGSH1.addCurveItem(name='GSH-1.FM-5', label="FM-5",
                                    corrSource="GSH-1.LJ-1_corr", corrField="GSH-1.FM-5", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH1.sensorProperties,
                                    pen=FM5Pen)
        FM6Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.magenta), width=1)
        self.graphGSH1.addCurveItem(name='GSH-1.FM-6', label="FM-6",
                                    corrSource="GSH-1.LJ-1_corr", corrField="GSH-1.FM-6", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH1.sensorProperties,
                                    pen=FM6Pen)

        self.controllerCB1W = CB1W(self.GUIInterface, "CB-1W Control", controllerName='CB-1W', parent=self, processGroups=["PAD-1"])
        self.layout.addWidget(self.controllerCB1W, 1, 0)
        self.controllerCB1S = CB1S(self.GUIInterface, "CB-1S Control", controllerName='CB-1S', parent=self, processGroups=["PAD-1"])
        self.layout.addWidget(self.controllerCB1S, 1, 1)
        self.controllerCB1T = CB1T(self.GUIInterface, "CB-1T Control", controllerName='CB-1T', parent=self, processGroups=["PAD-1"])
        self.layout.addWidget(self.controllerCB1T, 1, 2)

        self.controllerCB2W = CB2W(self.GUIInterface, "CB-2W Control", controllerName='CB-2W', parent=self, processGroups=["PAD-2"])
        self.layout.addWidget(self.controllerCB2W, 2, 0)
        self.controllerCB2S = CB2S(self.GUIInterface, "CB-2S Control", controllerName='CB-2S', parent=self, processGroups=["PAD-2"])
        self.layout.addWidget(self.controllerCB2S, 2, 1)
        self.controllerCB2T = CB2T(self.GUIInterface, "CB-2T Control", controllerName='CB-2T', parent=self, processGroups=["PAD-2"])
        self.layout.addWidget(self.controllerCB2T, 2, 2)

    def update(self):
        qtw.QWidget.update(self)