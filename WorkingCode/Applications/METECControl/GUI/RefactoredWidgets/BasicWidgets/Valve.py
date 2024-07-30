import enum
import math
from threading import RLock

import PyQt5.QtCore as QtCore
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.Modes import InputMode
from Applications.METECControl.GUI.RefactoredWidgets.Menus.SensorPropertiesMenu import SensorPropertiesMenu
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.QtMixin import ReceiverWidget, DataWidget, QtMixin
from PyQt5 import QtGui
from PyQt5 import QtWidgets as qtw
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QBrush, QPen, QPainter
from Utils.QtUtils import drawPolygon

VALVE_SIZE = 40
NAMEBOX_HEIGHT = 20

class ValveState(enum.Enum):
    powered = enum.auto()
    unpowered = enum.auto()
    transition = enum.auto()

class Valve(qtw.QWidget, ReceiverWidget, DataWidget, QtMixin):

    openValve = QtCore.pyqtSignal(str)
    closeValve = QtCore.pyqtSignal(str)
    valveClicked = QtCore.pyqtSignal(str)

    def __init__(self, GUIInterface,
                 name=None, parent=None, eventSource=None, labelOrientation='right', sensorProperties=None, ab=False,
                 *args, **kwargs):
        eventStreams = [{'source': eventSource, "channelType":ChannelType.Event}]

        QtMixin.__init__(self, GUIInterface=GUIInterface, name=name, parent=parent, *args, **kwargs)
        ReceiverWidget.__init__(self, GUIInterface=GUIInterface, name=name, eventStreams=eventStreams)
        qtw.QWidget.__init__(self, parent=parent)
        self.valveDiagram = ValveDiagram(self, ab)
        self.valveDiagram.clicksignal.connect(self.clicked)
        self.valveDiagram.rightClickSignal.connect(self.contextMenu)
        self.setMinimumSize(self.valveDiagram.minimumWidth(), self.valveDiagram.minimumHeight())
        # self.IDBox = qtw.QLabel(self.label)
        # self.IDBox.setMaximumHeight(NAMEBOX_HEIGHT)
        # self.IDBox.setContentsMargins(0,0,0,0)
        # self.IDBox.setAlignment(Qt.AlignCenter)

        if labelOrientation in ['top', 'bottom']:
            self.layout = qtw.QVBoxLayout()
        elif labelOrientation in ['left', 'right']:
            self.layout = qtw.QHBoxLayout()
        elif labelOrientation in [None, 'None']:
            self.layout = None

        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.state = ValveState.unpowered
        self.prevState = ValveState.powered

        self.sensorProperties = sensorProperties if sensorProperties else {}

        self.menu = None
        self.buildMenu()

        self.locked = False

        # numChars = len(self.label)
        # pxWidth = 15
        # self.setMaximumSize(VALVE_SIZE + numChars*pxWidth, VALVE_SIZE + NAMEBOX_HEIGHT)
        ## Trying another way to set the size:
        self.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)

        self.mode = InputMode.corrected

        self.timer = QtCore.QTimer()
        self.timerStopLater = False
        self.lock = RLock()

    def setRawMode(self):
        self.mode = InputMode.raw

    def localSetState(self, state):  # used by accept()
        # note: 0 is on, 1 is off. Adhere to this!
        if state == 0:
            estate = ValveState.powered
        else:
            estate = ValveState.unpowered

        if self.state is ValveState.transition and not (estate is self.prevState):
            self.setState(estate)
            self.timerStopLater = True
        elif self.state is not ValveState.transition:
            self.setState(estate)

    def setCorrValue(self, corrFieldname=None, corrValue=None):
        self.localSetState(corrValue)

    def setRawValue(self, rawFieldname=None, rawValue=None):
        self.menu.sensorprops.updateData({"Raw Value": rawValue})

    def update(self):
        qtw.QWidget.update(self)
        if self.timerStopLater:
            self.timer.stop()
        self.valveDiagram.update()

    def setState(self, state):
        with self.lock:
            if state in ValveState and state is not self.state:
                self.prevState = self.state
                self.state = state
                self.valveDiagram.setState(state)

    def clicked(self):
        self.valveClicked.emit(self.name)

    def togglePower(self):
        with self.lock:
            if self.locked:
                return
            if self.state == ValveState.transition:
                self.setState(self.prevState)
                if self.prevState == ValveState.powered:
                    self.prevState = ValveState.unpowered

                else:
                    self.prevState = ValveState.powered
            else:
                self.prevState = self.state
                self.setState(ValveState.transition)

            self.timer.timeout.connect(self.transitionTimer)
            self.timer.start(10000)
            self.timerStopLater = False
            if self.prevState == ValveState.powered:
                self.closeValve.emit(self.name)
            elif self.prevState == ValveState.unpowered:
                self.openValve.emit(self.name)
            else:
                pass # do nothing in transition state.

    def transitionTimer(self):
        if self.state == ValveState.transition:
            self.setState(self.prevState)
            if self.prevState == ValveState.powered:
                self.prevState = ValveState.unpowered
                self.openValve.emit(self.name)
            else:
                self.prevState = ValveState.powered
                self.closeValve.emit(self.name)
        self.timer.stop()

    def buildMenu(self):
        self.menu = qtw.QMenu()
        self.menu.checkbox = qtw.QAction("Lock", checkable=True)
        self.menu.checkbox.toggled.connect(self.setLock)
        self.menu.addAction(self.menu.checkbox)
        self.menu.sensorprops = SensorPropertiesMenu(GUIInterface=self.GUIInterface, name="ValveSensorProperties", parent=self.menu, sensorproperties=self.sensorProperties)
        self.menu.sensorprops.addData({"Raw Value": "NA"})
        self.menu.addMenu(self.menu.sensorprops)

    def contextMenu(self, ev):
        self.menu.popup(ev.globalPos())

    def setLock(self, lock):
        self.locked = lock
        self.valveDiagram.setLock(lock)
        self.menu.checkbox.setChecked(lock)

    def setExperimentLock(self, lock):
        self.setLock(lock)
        self.menu.checkbox.setDisabled(lock)


class ValveDiagram(qtw.QWidget):

    clicksignal = QtCore.pyqtSignal()
    rightClickSignal = QtCore.pyqtSignal(QtGui.QContextMenuEvent)

    def __init__(self, parent, ab=False, drawOutline=False, **kwargs):
        qtw.QWidget.__init__(self, parent)
        self.setMinimumSize(QSize(VALVE_SIZE, VALVE_SIZE))
        self.setMaximumSize(QSize(VALVE_SIZE, VALVE_SIZE))
        self.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)
        self.ab=ab
        self.locked = False
        self.state = ValveState.unpowered
        self.drawOutline = drawOutline
        self.parent = parent
        self.offColor = Qt.black
        self.onColor = Qt.white
        self.lockedColor = QtGui.QColor(190, 40, 40)
        self.painter = QPainter()
        self.blackPen = QPen(Qt.black, 3, Qt.SolidLine)
        self.grayPen = QPen(Qt.gray, 3, Qt.SolidLine)
        self.onBrush = QBrush(self.onColor)
        self.offBrush = QBrush(self.offColor)

    def setState(self, state):
        if state in ValveState:
            self.state = state
        self.update()

    def setLock(self, isLocked):
        self.locked = isLocked
        self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicksignal.emit()
        self.update()

    def contextMenuEvent(self, event):
        self.rightClickSignal.emit(event)

    def paintEvent(self, e):
        points = [
            (0.0, 0.0),
            (.5, math.sqrt(3) / 2.0),
            (-.5, math.sqrt(3) / 2.0)
        ]
        dims = self.geometry()
        scale = min(dims.width()/2.2, dims.height()/2.2)
        origin = [dims.width()/2.0, dims.height()/2.0]
        tailLength = .2

        self.painter.begin(self)

        if self.state == ValveState.powered:
            pen = self.blackPen
            sourceBrush = self.onBrush
            aBrush = self.offBrush
            bBrush = self.onBrush
        elif self.state == ValveState.unpowered:
            pen = self.blackPen
            sourceBrush = self.offBrush
            aBrush = self.onBrush
            bBrush = self.offBrush
        else:
            pen = self.grayPen
            sourceBrush = self.offBrush
            aBrush = self.offBrush
            bBrush = self.offBrush
        if self.ab and self.state != ValveState.transition:
            sourceBrush = self.onBrush

        self.painter.setPen(pen)

        self.painter.setBrush(bBrush)
        drawPolygon(self.painter, points, scale=scale, xyorigin=origin, rotateDegrees=180)
        drawPolygon(self.painter, [(0,math.sqrt(3)/2.0),(0, math.sqrt(3)/2.0+tailLength)], scale=scale, xyorigin=origin, rotateDegrees=180)

        self.painter.setBrush(sourceBrush)
        drawPolygon(self.painter, points, scale=scale, xyorigin=origin)
        drawPolygon(self.painter, [(0, math.sqrt(3) / 2.0), (0, math.sqrt(3) / 2.0 + tailLength)], scale=scale, xyorigin=origin,
                    rotateDegrees=0)

        if self.ab:
            self.painter.setBrush(aBrush)
            drawPolygon(self.painter, points, scale=scale, xyorigin=origin, rotateDegrees=270)
            drawPolygon(self.painter, [(0, math.sqrt(3) / 2.0), (0, math.sqrt(3) / 2.0 + tailLength)], scale=scale, xyorigin=origin,
                        rotateDegrees=270)

        if self.locked:
            pen = QPen(self.lockedColor, 3, Qt.SolidLine)
            pen.brush().setStyle(QtCore.Qt.NoBrush)
            self.painter.setBrush(QtGui.QBrush())
            self.painter.setPen(pen)
            square = (0,0,self.width()-1, self.height()-1)
            self.painter.drawRect(*square)

        self.painter.end()

