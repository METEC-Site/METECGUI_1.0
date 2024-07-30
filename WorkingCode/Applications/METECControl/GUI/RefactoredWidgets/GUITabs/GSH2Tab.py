import pyqtgraph
from Applications.METECControl.GUI.RefactoredWidgets.Controllers.GSHS import GSH2
from Applications.METECControl.GUI.RefactoredWidgets.Controllers.Pad3 import CB3W, CB3S, CB3T
from Applications.METECControl.GUI.RefactoredWidgets.Controllers.Pad6 import CB6D, CB6C, CB6S
from Applications.METECControl.GUI.RefactoredWidgets.Graphs.BasicGraph import BasicGraph
from Framework.BaseClasses.QtMixin import QtMixin
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
from PyQt5 import QtWidgets as qtw


class GSH2Tab(qtw.QWidget, QtMixin):

    def __init__(self, GUIInterface, name=None, parent=None):
        QtMixin.__init__(self, GUIInterface, name=name, parent=parent)
        qtw.QWidget.__init__(self, parent=parent)
        self.layout = qtw.QGridLayout()
        self.setLayout(self.layout)
        self.buildGUI()

    def buildGUI(self):
        self.controllerGSH2 = GSH2(self.GUIInterface, "GSH-2 Control", controllerName='GSH-2', parent=self, processGroups=["PAD-3", "PAD-6"])
        self.layout.addWidget(self.controllerGSH2, 0, 0)

        self.graphGSH2 = BasicGraph(self.GUIInterface, "GSH-2 Graph", controllerName="GSH-2", parent=self,
                                    label="GSH-2")
        self.layout.addWidget(self.graphGSH2, 0, 1, 1, 2)

        FM1Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.red), width=1)
        self.graphGSH2.addCurveItem(name='GSH-2.FM-1', label="FM-1",
                                    corrSource="GSH-2.LJ-1_corr", corrField="GSH-2.FM-1", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH2.sensorProperties,
                                    pen=FM1Pen)
        FM2Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.yellow), width=1)
        self.graphGSH2.addCurveItem(name='GSH-2.FM-2', label="FM-2",
                                    corrSource="GSH-2.LJ-1_corr", corrField="GSH-2.FM-2", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH2.sensorProperties,
                                    pen=FM2Pen)
        FM3Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.white), width=1)
        self.graphGSH2.addCurveItem(name='GSH-2.FM-3', label="FM-3",
                                    corrSource="GSH-2.LJ-1_corr", corrField="GSH-2.FM-3", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH2.sensorProperties,
                                    pen=FM3Pen)
        FM4Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.gray), width=1)
        self.graphGSH2.addCurveItem(name='GSH-2.FM-4', label="FM-4",
                                    corrSource="GSH-2.LJ-1_corr", corrField="GSH-2.FM-4", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH2.sensorProperties,
                                    pen=FM4Pen)
        FM5Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.cyan), width=1)
        self.graphGSH2.addCurveItem(name='GSH-2.FM-5', label="FM-5",
                                    corrSource="GSH-2.LJ-1_corr", corrField="GSH-2.FM-5", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH2.sensorProperties,
                                    pen=FM5Pen)
        FM6Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.magenta), width=1)
        self.graphGSH2.addCurveItem(name='GSH-2.FM-6', label="FM-6",
                                    corrSource="GSH-2.LJ-1_corr", corrField="GSH-2.FM-6", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH2.sensorProperties,
                                    pen=FM6Pen)

        self.controllerCB6D = CB6D(self.GUIInterface, "CB-6D Control", controllerName='CB-6D', parent=self, processGroups=["PAD-6"])
        self.layout.addWidget(self.controllerCB6D, 1, 0)
        self.controllerCB6C = CB6C(self.GUIInterface, "CB-6C Control", controllerName='CB-6C', parent=self, processGroups=["PAD-6"])
        self.layout.addWidget(self.controllerCB6C, 1, 1)
        self.controllerCB6S = CB6S(self.GUIInterface, "CB-6S Control", controllerName='CB-6S', parent=self, processGroups=["PAD-6"])
        self.layout.addWidget(self.controllerCB6S, 1, 2)

        self.controllerCB3W = CB3W(self.GUIInterface, "CB-3W Control", controllerName='CB-3W', parent=self, processGroups=["PAD-3"])
        self.layout.addWidget(self.controllerCB3W, 2, 0)
        self.controllerCB3S = CB3S(self.GUIInterface, "CB-3S Control", controllerName='CB-3S', parent=self, processGroups=["PAD-3"])
        self.layout.addWidget(self.controllerCB3S, 2, 1)
        self.controllerCB3T = CB3T(self.GUIInterface, "CB-3T Control", controllerName='CB-3T', parent=self, processGroups=["PAD-6", "Pad-3"])
        self.layout.addWidget(self.controllerCB3T, 2, 2)

    def update(self):
        qtw.QWidget.update(self)
        # self.graphGSH2.update()
        # self.controllerGSH2.update()
        # self.controllerCB6D.update()
        # self.controllerCB6C.update()
        # self.controllerCB6S.update()
        # self.controllerCB3W.update()
        # self.controllerCB3S.update()
        # self.controllerCB3T.update()