import pyqtgraph
from Applications.METECControl.GUI.RefactoredWidgets.Controllers.GSHS import GSH4
from Applications.METECControl.GUI.RefactoredWidgets.Controllers.Pad7 import CB7P1, CB7P2, CB7P3, CB7P4
from Applications.METECControl.GUI.RefactoredWidgets.Graphs.BasicGraph import BasicGraph
from Framework.BaseClasses.QtMixin import QtMixin
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
from PyQt5 import QtWidgets as qtw


class GSH4Tab(qtw.QWidget, QtMixin):

    def __init__(self, GUIInterface, name=None, parent=None):
        QtMixin.__init__(self, GUIInterface, name=name, parent=parent)
        qtw.QWidget.__init__(self, parent=parent)
        self.layout = qtw.QGridLayout()
        self.setLayout(self.layout)
        self.buildGUI()

    def buildGUI(self):
        self.controllerGSH4 = GSH4(self.GUIInterface, "GSH-4 Control", controllerName='GSH-4', parent=self, processGroups=["PAD-7"])
        self.layout.addWidget(self.controllerGSH4, 0, 0)

        self.graphGSH4 = BasicGraph(self.GUIInterface, "GSH-4 Graph", controllerName="GSH-4", parent=self,
                                    label="GSH-4")
        self.layout.addWidget(self.graphGSH4, 0, 1, 1, 2)

        FM1Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.red), width=1)
        self.graphGSH4.addCurveItem(name='GSH-4.FM-1', label="FM-1",
                                    corrSource="GSH-4.LJ-1_corr", corrField="GSH-4.FM-1", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH4.sensorProperties,
                                    pen=FM1Pen)
        FM2Pen = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.yellow), width=1)
        self.graphGSH4.addCurveItem(name='GSH-4.FM-2', label="FM-2",
                                    corrSource="GSH-4.LJ-1_corr", corrField="GSH-4.FM-2", corrUnits="SLPM",
                                    outputGrouping=None, sensorProperties=self.controllerGSH4.sensorProperties,
                                    pen=FM2Pen)

        self.controllerCB7P1 = CB7P1(self.GUIInterface, "CB-7P1 Control", controllerName='CB-7P1', parent=self, processGroups=["PAD-7"])
        self.layout.addWidget(self.controllerCB7P1, 1, 0)
        self.controllerCB7P2 = CB7P2(self.GUIInterface, "CB-7P2 Control", controllerName='CB-7P2', parent=self, processGroups=["PAD-7"])
        self.layout.addWidget(self.controllerCB7P2, 1, 1)
        self.controllerCB7P3 = CB7P3(self.GUIInterface, "CB-7P3 Control", controllerName='CB-7P3', parent=self, processGroups=["PAD-7"])
        self.layout.addWidget(self.controllerCB7P3, 2, 0)
        self.controllerCB7P4 = CB7P4(self.GUIInterface, "CB-7P4 Control", controllerName='CB-7P4', parent=self, processGroups=["PAD-7"])
        self.layout.addWidget(self.controllerCB7P4, 2, 1)

    def update(self):
        qtw.QWidget.update(self)
        # self.graphGSH4.update()
        # self.controllerGSH4.update()
        # self.controllerCB7P1.update()
        # self.controllerCB7P2.update()
        # self.controllerCB7P3.update()
        # self.controllerCB7P4.update()