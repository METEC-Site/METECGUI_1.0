import PyQt5.QtCore as qtc
import pyqtgraph
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.ScrollWidget import ScrollWidget
from Applications.METECControl.GUI.RefactoredWidgets.Graphs.BasicGraph import BasicGraph
from PyQt5 import QtGui as qtg
from PyQt5 import QtWidgets as qtw


class METTab(ScrollWidget):

    def __init__(self, GUIInterface, name=None, parent=None):
        ScrollWidget.__init__(self, GUIInterface, name=name, parent=parent)
        self.layout = qtw.QGridLayout()
        self.direction = 0
        #temporary met fake data arrays for testing

        self.setLayout(self.layout)
        #build gui
        self.metPlot = BasicGraph(GUIInterface, 'MET', controllerName="MET-2.LJ-1")
        self.layout.addWidget(self.metPlot,0,0)

        uws = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.blue), width=1)
        self.uws = self.metPlot.addCurveItem('UWS', corrSource='MET-2.LJ-1', corrField='MET-2.UWS', pen=uws)
        vws = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.red), width=1)
        self.vws = self.metPlot.addCurveItem("VWS", corrSource='MET-2.LJ-1', corrField='MET-2.VWS', pen=vws)
        wws = pyqtgraph.mkPen(qtg.QColor(qtc.Qt.green), width=1)
        self.wws = self.metPlot.addCurveItem("WWS", corrSource='MET-2.LJ-1', corrField='MET-2.WWS', pen=wws)
        # self.windRose1 = WindRose(self.GUIInterface, "MET-1", self)
        # self.windRose2 = WindRose(self.GUIInterface, "MET-2", self)
        # self.windVane = WindVane(self.GUIInterface, "Wind Vane", self)
        # self.layout.addWidget(self.windVane, 1, 1, 1, 1, alignment=qtc.Qt.AlignTop | qtc.Qt.AlignLeft)
        # self.layout.addWidget(self.windRose1, 1, 2, 1, 1, alignment=qtc.Qt.AlignTop | qtc.Qt.AlignLeft)
        # self.layout.addWidget(self.windRose2, 1, 3, 1, 1, alignment=qtc.Qt.AlignTop | qtc.Qt.AlignLeft)
        # self.graphMet1 = BasicGraph(GUIInterface=GUIInterface, name="Met 1 graph", parent=self)
        # self.layout.addWidget(self.graphMet1, 2, 1, 1, 3)
        # self.graphMet2 = BasicGraph(GUIInterface=GUIInterface, name="Met 2 graph", parent=self)
        # self.layout.addWidget(self.graphMet2, 3, 1, 1, 3)
        # self.legend = ChannelLegend(self, {"channel 1": {"units": "m/s"}, "channel 2": {"units": "m/s"}})
        # self.layout.addWidget(self.legend, 2, 4, 2, 1)

    def update(self):
        ScrollWidget.update(self)
        self.windRose1.update()
        # self.generateFakeData()  # temporary for testing
        # self.windVane.update()


class ChannelLegend(qtw.QWidget):

    def __init__(self, parent=None, channels=None):
        qtw.QWidget.__init__(self, parent)
        self.setLayout(qtw.QHBoxLayout())
        if channels is None:
            channels = {}
        self.channels = channels
        self.channelList = qtw.QListWidget()
        for channelName, values in channels.items():
            label = qtw.QLabel(channelName)
            item = qtw.QListWidgetItem()
            item.setSizeHint(label.sizeHint())
            self.channelList.addItem(item)
            self.channelList.setItemWidget(item, label)
        self.layout().addWidget(self.channelList)