import logging
from abc import ABC, abstractmethod

from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.ControlPanel import ControlPanel
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.Valve import Valve
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.QtMixin import ReceiverWidget
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from PyQt5.QtGui import QFont


class Controller(qtw.QFrame, ReceiverWidget, ABC):
    def __init__(self, GUIInterface,
                 name=None, parent=None, controllerName=None, processGroups=None,
                 rawSource=None, corrSource=None, commandSource=None, *args, **kwargs):

        self.rawSource = rawSource if not rawSource is None else f"{controllerName}.LJ-1"
        self.corrSource = corrSource if not corrSource is None else f"{controllerName}.LJ-1_corr"
        self.commandSource = commandSource if not commandSource is None else f"{controllerName}.LJ-1"

        rawDataStreams = [{'source': self.rawSource, "channelType": ChannelType.Data}]
        corrDataStreams = [{'source': self.rawSource, "channelType": ChannelType.Data}]
        commandStreams = [{'source': self.rawSource, "channelType": ChannelType.Command}]
        ReceiverWidget.__init__(self, GUIInterface=GUIInterface, name=name, parent=parent,
                                commandStreams=commandStreams, rawDataStreams=rawDataStreams,
                                corrDataStreams=corrDataStreams, *args, **kwargs)
        qtw.QFrame.__init__(self, parent)

        self.sensorProperties = self.GUIInterface.getSourceInfoCommand(commandDest=self.commandSource)
        if not self.sensorProperties:
            self.sensorProperties = {}

        self.ctrlName = controllerName

        # Initializing the frame style.
        self.setFrameShape(qtw.QFrame.Box)
        self.setFrameShadow(qtw.QFrame.Raised)
        # self.setStyleSheet('border:1px solid rgb(0, 0, 0);')
        self.setLineWidth(2)
        self.setMidLineWidth(1)

        # # add a widget containing a 'stop' and 'connection status' button.
        self.timer = qtc.QTimer()

    def buildGUI(self):
        self._buildContainer()
        self._buildValves()
        self._buildPTs()
        self._buildTCs()
        self._buildShutoffButton()
        for widgetName, widget in self.outputWidgets.items():
            if type(widget) is Valve:
                widget.closeValve.connect(self.handleValveClosed)
                widget.openValve.connect(self.handleValveOpened)
                widget.valveClicked.connect(self.handleValveClicked)

    def padShutdown(self, processGroup):
        allChildren = self.findChildren(qtc.QObject)
        valves = list(filter(lambda x: type(x) == Valve, allChildren))
        for valve in valves:
            if not valve.locked:
                valve.closeValve.emit(valve.name)

    def getSensorProperties(self, sensorName):
        return self.sensorProperties.get(sensorName, {})

    @qtc.pyqtSlot(str)
    def handleValveClosed(self, valveName):
        self.GUIInterface.closeValve(self.commandSource, args=[valveName])

    @qtc.pyqtSlot(str)
    def handleValveOpened(self, valveName):
        self.GUIInterface.openValve(self.commandSource, args=[valveName])

    @qtc.pyqtSlot(str)
    def handleValveClicked(self, valveName):
        if self.GUIInterface.checkLocked(self.commandSource): # todo: add proper name here.
            return
        self.toggleValve(valveName)

    def toggleValve(self, valveName):
        widget = self.outputWidgets[valveName]
        widget.togglePower()

    def _buildContainer(self):
        # Setting the layout that will contain all other widgets and layouts.
        self.containerLayout = qtw.QGridLayout()
        self.containerLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.containerLayout)

        # Adding a label to the top area of the frame
        self.textLabel = qtw.QLabel(self)
        self.textLabel.setAlignment(qtc.Qt.AlignCenter)
        self.textLabel.setText(self.label)
        # self.textLabel.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum) # todo: commented to see if this fixes the tiny widget size problem.
        self.textLabel.setMaximumHeight(70)

        labelFont = QFont()
        labelFont.setBold(True)
        labelFont.setPointSize(14)
        self.textLabel.setFont(labelFont)

        # Adding a main container widget to the bottom of the frame
        self.mainWidget = qtw.QWidget(self)
        self.mainLayout = qtw.QHBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainWidget.setLayout(self.mainLayout)
        # self.mainWidget.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.MinimumExpanding)

        self.inletValveWidget = qtw.QWidget(self)
        self.inletValveLayout = qtw.QGridLayout()
        self.inletValveWidget.setLayout(self.inletValveLayout)
        self.inletValveLayout.setContentsMargins(0, 0, 0, 0)

        self.ptContainer = qtw.QWidget(self)
        self.ptLayout = qtw.QHBoxLayout()
        self.ptContainer.setLayout(self.ptLayout)
        self.ptLayout.setContentsMargins(0, 0, 0, 0)

        self.tcContainer = qtw.QWidget(self)
        self.tcLayout = qtw.QHBoxLayout()
        self.tcContainer.setLayout(self.tcLayout)
        self.tcLayout.setContentsMargins(0, 0, 0, 0)

        self.valveManifoldContainer = qtw.QWidget(self)
        self.valveManifoldLayout = qtw.QGridLayout()
        self.valveManifoldContainer.setLayout(self.valveManifoldLayout)
        self.valveManifoldLayout.setContentsMargins(0, 0, 0, 0)

        self.mainLayout.addWidget(self.inletValveWidget)
        self.mainLayout.addWidget(self.ptContainer)
        self.mainLayout.addWidget(self.tcContainer)
        self.mainLayout.addWidget(self.valveManifoldContainer)

        # self.connectionWidget = ControlPanel(self.GUIInterface, name=f"{self.name}ControlPanel", parent=self, processGroups=self.processGroups)

        # Adding child layouts to the container layout and showing everything
        self.containerLayout.setContentsMargins(0, 0, 0, 0)
        self.containerLayout.addWidget(self.textLabel, 0, 0)
        self.containerLayout.addWidget(self.mainWidget, 1, 0)
        # self.containerLayout.addWidget(self.connectionWidget, 2, 0)

        self.outputWidgets = {}

    @abstractmethod
    def _buildValves(self):
        pass

    @abstractmethod
    def _buildPTs(self):
        pass

    @abstractmethod
    def _buildTCs(self):
        pass

    def _buildShutoffButton(self):
        self.controlWidget = ControlPanel(GUIInterface=self.GUIInterface, name=f'Controller - {self.name}', parent=self, readerName=self.commandSource)
        self.containerLayout.addWidget(self.controlWidget, 2, 0)


    def update(self):
        qtw.QFrame.update(self)
        self.textLabel.update()
        for widgetName, widget in self.outputWidgets.items():
            try:
                latestcorrTS, latestCorrected = self.GUIInterface.getLatestValue(self.corrSource, widgetName)
                latestRawTS, latestRaw = self.GUIInterface.getLatestValue(self.rawSource, widgetName)
                widget.setRawValue(rawFieldname=widgetName, rawValue=latestRaw)
                widget.setCorrValue(corrFieldname=widgetName, corrValue=latestCorrected)
            except Exception as e:
                logging.error(e)
        # if self.controlPanel:
        #     self.controlWidget.update()
        self.mainWidget.update()
