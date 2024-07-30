import pyqtgraph
from Applications.METECControl.GUI.RefactoredWidgets.Controllers.GSHS import GSH3
from Applications.METECControl.GUI.RefactoredWidgets.Controllers.Pad4 import CB4W, CB4S, CB4T
from Applications.METECControl.GUI.RefactoredWidgets.Controllers.Pad5 import CB5W, CB5S
from Applications.METECControl.GUI.RefactoredWidgets.Graphs.BasicGraph import BasicGraph
from Framework.BaseClasses.QtMixin import QtMixin
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
from PyQt5 import QtWidgets as qtw


class GSH3Tab(qtw.QWidget, QtMixin):

    def __init__(self, GUIInterface, name=None, parent=None):
        QtMixin.__init__(self, GUIInterface, name=name, parent=parent)
        qtw.QWidget.__init__(self, parent=parent)
        self.layout = qtw.QGridLayout()
        self.setLayout(self.layout)
        self.buildGUI()

    def buildGUI(self):
        self.controllerGSH3 = GSH3(self.GUIInterface, "GSH-3 Control", controllerName='GSH-3', parent=self, processGroups=["PAD-4", "PAD-5"])
        self.layout.addWidget(self.controllerGSH3, 0, 0)

        self.graphGSH3 = BasicGraph(self.GUIInterface, "GSH-3 Graph", controllerName="GSH-3", parent=self,
                                    label="GSH-3")
        self.layout.addWidget(self.graphGSH3, 0, 1, 1, 2)

        FM1Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.red), width=1)
        self.graphGSH3.addCurveItem(name='GSH-3.FM-1', label="FM-1",
                                    corrSource="GSH-3.LJ-1_corr", corrField="GSH-3.FM-1", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH3.sensorProperties,
                                    pen=FM1Pen)
        FM2Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.yellow), width=1)
        self.graphGSH3.addCurveItem(name='GSH-3.FM-2', label="FM-2",
                                    corrSource="GSH-3.LJ-1_corr", corrField="GSH-3.FM-2", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH3.sensorProperties,
                                    pen=FM2Pen)
        FM3Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.white), width=1)
        self.graphGSH3.addCurveItem(name='GSH-3.FM-3', label="FM-3",
                                    corrSource="GSH-3.LJ-1_corr", corrField="GSH-3.FM-3", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH3.sensorProperties,
                                    pen=FM3Pen)
        FM4Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.green), width=1)
        self.graphGSH3.addCurveItem(name='GSH-3.FM-4', label="FM-4",
                                    corrSource="GSH-3.LJ-1_corr", corrField="GSH-3.FM-4", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH3.sensorProperties,
                                    pen=FM4Pen)
        FM5Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.cyan), width=1)
        self.graphGSH3.addCurveItem(name='GSH-3.FM-5', label="FM-5",
                                    corrSource="GSH-3.LJ-1_corr", corrField="GSH-3.FM-5", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH3.sensorProperties,
                                    pen=FM5Pen)

        FM6Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.magenta), width=1)
        self.graphGSH3.addCurveItem(name='GSH-3.FM-6', label="FM-6",
                                    corrSource="GSH-3.LJ-1_corr", corrField="GSH-3.FM-6", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH3.sensorProperties,
                                    pen=FM6Pen)

        FM7Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.darkRed), width=1)
        self.graphGSH3.addCurveItem(name='GSH-3.FM-7', label="FM-7",
                                    corrSource="GSH-3.LJ-1_corr", corrField="GSH-3.FM-7", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH3.sensorProperties,
                                    pen=FM7Pen)

        FM8Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.darkYellow), width=1)
        self.graphGSH3.addCurveItem(name='GSH-3.FM-8', label="FM-8",
                                    corrSource="GSH-3.LJ-1_corr", corrField="GSH-3.FM-8", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH3.sensorProperties,
                                    pen=FM8Pen)

        FM9Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.darkBlue), width=1)
        self.graphGSH3.addCurveItem(name='GSH-3.FM-9', label="FM-9",
                                    corrSource="GSH-3.LJ-1_corr", corrField="GSH-3.FM-9", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH3.sensorProperties,
                                    pen=FM9Pen)

        FM10Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.darkGreen), width=1)
        self.graphGSH3.addCurveItem(name='GSH-3.FM-10', label="FM-10",
                                    corrSource="GSH-3.LJ-1_corr", corrField="GSH-3.FM-10", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH3.sensorProperties,
                                    pen=FM10Pen)

        self.controllerCB4W = CB4W(self.GUIInterface, "CB-4W Control", controllerName='CB-4W', parent=self, processGroups=["PAD-4"])
        self.layout.addWidget(self.controllerCB4W, 1, 0)
        self.controllerCB4S = CB4S(self.GUIInterface, "CB-4S Control", controllerName='CB-4S', parent=self, processGroups=["PAD-4"])
        self.layout.addWidget(self.controllerCB4S, 1, 1)
        self.controllerCB4T = CB4T(self.GUIInterface, "CB-4T Control", controllerName='CB-4T', parent=self, processGroups=["PAD-4", "PAD-5"])
        self.layout.addWidget(self.controllerCB4T, 1, 2)

        self.controllerCB5W = CB5W(self.GUIInterface, "CB-5W Control", controllerName='CB-5W', parent=self, processGroups=["PAD-5"])
        self.layout.addWidget(self.controllerCB5W, 2, 0)
        self.controllerCB5S = CB5S(self.GUIInterface, "CB-5S Control", controllerName='CB-5S', parent=self, processGroups=["PAD-5"])
        self.layout.addWidget(self.controllerCB5S, 2, 1)

    def update(self):
        qtw.QWidget.update(self)
        # self.graphGSH3.update()
        # self.controllerGSH3.update()
        # self.controllerCB4W.update()
        # self.controllerCB4S.update()
        # self.controllerCB4T.update()
        # self.controllerCB5W.update()
        # self.controllerCB5S.update()