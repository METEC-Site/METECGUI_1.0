from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.UnitOutputBox import UnitOutputBox
from Applications.METECControl.GUI.RefactoredWidgets.Menus.SensorPropertiesMenu import SensorPropertiesMenu
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.QtMixin import QtMixin
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui
from PyQt5 import QtWidgets as qtw
from PyQt5.QtWidgets import QVBoxLayout


class GraphLegendWidget(qtw.QFrame, QtMixin):
    unitChanged = qtc.pyqtSignal(str)
    axisChanged = qtc.pyqtSignal(str)

    def __init__(self, GUIInterface,
                 name=None, parent=None, label=None, color=None, unitDict={}, sensorproperties=None,
                 corrSource=None, corrField=None, corrUnits=None,
                 rawSource=None, rawField=None, rawUnits=None,
                 *args, **kwargs):
        QtMixin.__init__(self, GUIInterface, name=name, parent=parent, *args, **kwargs)
        qtw.QFrame.__init__(self, parent)

        self.corrSource = corrSource
        self.corrField  = corrField
        self.corrUnits  = corrUnits
        self.rawSource  = rawSource
        self.rawField   = rawField
        self.rawUnits   = rawUnits

        self.sp = qtw.QSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)
        self.label = label if label else name
        self.sensorproperties = sensorproperties
        self.unitDict = unitDict
        self.color = color

        self._setupFrame()
        self._setupUOB()
        self._setupNamebox()
        self._setupColorWidget()
        self._setupAxisCombo()

        self.visible = False

    def _setupFrame(self):
        self.setAutoFillBackground(True)
        self.setFrameShape(qtw.QFrame.Box)
        self.setFrameShadow(qtw.QFrame.Raised)
        self.setLineWidth(3)
        self.setMidLineWidth(2)
        self.gridLayout = qtw.QGridLayout(self)
        self.gridLayout.setContentsMargins(1, 1, 1, 1)
        self.gridLayout.setSpacing(1)
        self.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)
        # self.setFixedWidth(230)

    def _setupUOB(self):
        self.outputBox = UnitOutputBox(self.GUIInterface, name=self.name + 'UnitOutputBox', parent=self, units=self.corrUnits, unitDict=self.unitDict)
        self.outputBox.unitChanged.connect(self.updateUnits)
        self.outputBox.setMinimumWidth(130)
        self.gridLayout.addWidget(self.outputBox, 2, 0, 1, 2)

    def _setupNamebox(self):
        self.nameBox = qtw.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.nameBox.setFont(font)
        self.nameBox.setText(f' {self.label} ')
        self.nameBox.adjustSize()
        self.nameBox.setSizePolicy(self.sp)
        self.nameBox.setFrameShape(qtw.QFrame.Panel)
        self.nameBox.setAlignment(qtc.Qt.AlignCenter)
        self.nameBox.contextMenuEvent = self.nameboxMenu
        self.nameBox.menu = None
        self.gridLayout.addWidget(self.nameBox, 0, 0, 1, 2)

    def _setupColorWidget(self):
        self.colorWidget = qtw.QWidget(self)
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Background, self.color)
        self.colorWidget.setPalette(palette)
        self.colorWidget.setAutoFillBackground(True)
        self.colorWidget.setSizePolicy(self.sp)
        self.colorWidget.contextMenuEvent = self.colorMenuRightClick
        self.gridLayout.addWidget(self.colorWidget, 1, 0, 1, 1)
        self.colorWidget.setMaximumSize(70, 40)

    def _setupAxisCombo(self):
        self.axisCombo = qtw.QComboBox(self)
        self.axisCombo.addItem("Right Axis")
        self.axisCombo.addItem("Left Axis")
        font = QtGui.QFont()
        font.setPointSize(8)
        self.axisCombo.setFont(font)
        self.axisCombo.wheelEvent = lambda ev: ev.ignore()
        self.axisCombo.setSizePolicy(qtw.QSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum))
        self.axisCombo.setMaximumSize(75, 40)
        self.axisCombo.currentTextChanged.connect(lambda x: self.axisChanged.emit(x))
        self.gridLayout.addWidget(self.axisCombo, 1, 1, 1, 1)

    def update(self):
        latestTS, latestVal = self.GUIInterface.getLatestValue(sourceName=self.corrSource, fieldName=self.corrField)
        self.outputBox.changeValue(inputValue=latestVal)

    def updateUnits(self, unitAbbr):  # called by outputbox unit change
        self.unitChanged.emit(unitAbbr)

    def changeUnit(self, unitAbbr):
        self.outputBox.changeUnit(unitAbbr)

    def toggle(self):
        self.visible = not self.visible
        # if not self.visible:
        #     self.pushButton.setText("Show")
        # if self.visible:
        #     self.pushButton.setText("Hide")

    def colorMenuRightClick(self, event):
        colorpick = qtw.QColorDialog()
        # colorpick.setWindowFlags(qtc.Qt.WindowStaysOnTopHint)
        color=colorpick.getColor() #qcolor
        if color.isValid():
            self.parent.curveColorUpdate(self, color)
            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.Background, color)
            self.colorWidget.setPalette(palette)

    def nameboxMenu(self, ev):
        if not self.nameBox.menu:
            self.nameBox.menu = qtw.QMenu()
            if self.sensorproperties:
                self.nameBox.menu.sensorprops = SensorPropertiesMenu(GUIInterface=self.GUIInterface, name="GraphLegendSensors", parent=self.nameBox.menu, sensorproperties=self.sensorproperties)
                self.nameBox.menu.addMenu(self.nameBox.menu.sensorprops)
        self.nameBox.menu.popup(ev.globalPos())


class AlicatLegendWidget(GraphLegendWidget):

    def __init__(self, GUIInterface,
                 name=None, parent=None, unitDict=None,
                 *args, **kwargs):
        GraphLegendWidget.__init__(self, GUIInterface, name, parent, unitDict, *args, **kwargs)
        self.unitDict = unitDict

        self.setpointBox = qtw.QWidget(self)
        self.setpointLayout = qtw.QGridLayout(self.setpointBox)
        self.setpointLayout.setContentsMargins(0, 0, 0, 0)
        self.setpointLayout.setSpacing(0)

        self.setpointLabel = qtw.QLabel(self.setpointBox)
        self.setpointLabel.setText('Setpt: ')
        self.setInput = BoundedSpinBox(self.setpointBox)

        self.setpointLayout.addWidget(self.setpointLabel, 0,0,1,1)
        self.setpointLayout.addWidget(self.setInput, 0,1,1,1)


        self.setButton = qtw.QPushButton(self)
        self.setButton.setText('Input')
        self.setButton.setMaximumSize(60, 40)
        self.setButton.setSizePolicy(qtw.QSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum))
        self.setButton.adjustSize()
        self.setButton.clicked.connect(self.setSetpoint)

        self.gridLayout.addWidget(self.setpointBox, 2, 0, 1, 1)
        self.gridLayout.addWidget(self.setButton, 2, 1, 1, 1)

    def keyPressEvent(self, event):
        if event.key() == qtc.Qt.Key_Return:
            self.setSetpoint(event)
            self.setInput.clearFocus()
        else:
            GraphLegendWidget.keyPressEvent(self, event)

    def setSetpoint(self, event):
        val = self.setInput.value()
        comStream = self._getStreamInfo(ChannelType.Command, streamType='controller')
        comDest = comStream['source']
        self.GUIInterface.setSetpoint(comDest, args=[val])

    def validate(self, text, position):
        return

class OutputGroupings(qtw.QWidget, QtMixin):
    newOutputGrouping = qtc.pyqtSignal(str)

    def __init__(self, GUIInterface, name=None, parent=None, groupings=None, visible=True, *args, **kwargs):
        QtMixin.__init__(self, GUIInterface, name=name, parent=parent, *args, **kwargs)
        qtw.QWidget.__init__(self, parent)
        self.setGeometry(100, 100, 200, 200)
        self.groupings = groupings if groupings else {}  # Dictionary of group names with lists of radioboxes as items

        self.boxes = {}  # Dictionary of groupboxes with their checkbox children and ungrouped checkboxes

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.outputGrouping = None
        self.createGroupings()
        self.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)
        self.visible = True

    def createGroupings(self):
        """
        called by addCheckbox and  init
        Takes all checkboxes in groupings (key = string group, values = list of CurveCheckbox widgets)
        and gives them a CurveGroupbox widget if key is not None
        """
        foundGroup=False
        self.outputGrouping=None
        for key, value in self.groupings.items():
            if key is not None and len(self.groupings.keys()) > 1:
                gb = CurveGroupBox(key, self)
                gb.setCheckable(True)
                gblayout = QVBoxLayout()
                self.boxes[gb] = []
                for cb in value:
                    cb.container = self
                    cb.groupbox = gb
                    gb.checkboxes.append(cb)
                    self.boxes[gb].append(cb)
                    if gb.isChecked():
                        cb.setChecked(True)
                    gblayout.addWidget(cb)

                if not foundGroup:
                    foundGroup = True
                    self.outputGrouping = key
                    gb.setChecked(True)
                else:
                    gb.setChecked(False)

                gb.setLayout(gblayout)
                self.layout.addWidget(gb)
            elif key is not None:
                for cb in self.groupings[key]:
                    cb.container = self
                    if not foundGroup:
                        cb.setChecked(True)
                        foundGroup = True
                    else:
                        cb.setChecked(False)
                    self.layout.addWidget(cb)
                    self.boxes[cb] = [cb]

        nogroup = self.groupings.get(None)
        if nogroup:
            for cb in self.groupings[None]:
                cb.container = self
                if not foundGroup:
                    cb.setChecked(True)
                    foundGroup=True
                else:
                    cb.setChecked(False)
                self.layout.addWidget(cb)
                self.boxes[cb] = [cb]

    def addCheckbox(self, cb, group=None):
        """
        add's a checkbox to the organizer
        deletes existing group boxes to re-organize in case it's needed
        :param cb: checkbox that's being added to the group organizer
        :param group: the group that the checkbox is being added to
        :return: None
        """
        cb.container = self
        if type(cb) == CurveCheckbox:
            group = cb.getGroup()
        if group not in self.groupings.keys():
            self.groupings[group] = []
        for key, value in self.boxes.items():
            for v in value:
                v.setParent(None)
                del v
            del value
            key.setParent(None)
            del key
        del self.boxes
        self.boxes = {}
        self.groupings[group].append(cb)
        self.createGroupings()

    def swapToGroup(self, checkedbox):
        """
        takes Checkbox or group box,
        sets outputGrouping to group of box (self or it's parent groupbox)
        if desired, can call uncheckOtherboxes to force only one group active
        :param checkedbox: swaps outputGrouping to this box
        :return:
        """
        self.outputGrouping = checkedbox.group
        self.newOutputGrouping.emit(self.outputGrouping)

        # uncheck other boxes does what you expect. Uncomment if you want exclusively one group
        # if checkedbox in self.boxes.keys():
        #     self.uncheckOtherBoxes(checkedbox)

    def uncheckOtherBoxes(self, checkedbox):
        """
        unchecks and turns off otherboxes
        :param checkedbox: must be a groupbox or ungrouped box, unchecks and sets visible to False for other boxes
        :return:
        """
        for box in self.boxes.keys():
            if box != checkedbox and box.isChecked():
                box.setChecked(False)

class BoundedSpinBox(qtw.QDoubleSpinBox):
    def __init__(self, parent):
        qtw.QDoubleSpinBox.__init__(self, parent)
        self.validator = QtGui.QDoubleValidator(self)

    def validate(self, p_str, p_int):
        value = None
        try:
            isOk = True
            value = float(p_str)
        except:
            isOk = False
        if isOk:
            if value >= self.minimum() and value <= self.maximum():
                return (self.validator.Acceptable, p_str, p_int)
            return (self.validator.Intermediate, p_str, p_int)
        else:
            return qtw.QDoubleSpinBox.validate(self, p_str, p_int)
        pass

    def fixup(self, p_str):
        value = None
        try:
            isOk = True
            value = float(p_str)
        except:
            isOk = False
        if isOk:
            if value < self.minimum():
                value = self.minimum()
            if value > self.maximum():
                value = self.maximum()
            return p_str.replace(p_str, str(value))
        else:
            return qtw.QDoubleSpinBox.fixup(self, p_str)


class CurveGroupBox(qtw.QGroupBox):
    newStateSignal = qtc.pyqtSignal(bool)

    def __init__(self, name, container):
        qtw.QGroupBox.__init__(self, name)
        self.name = name
        self.checkboxes = []
        self.group = name
        self.container = container
        self.toggled.connect(self.newState)

    def getChecked(self):
        return self.isChecked()

    def newState(self, state):
        """
        Listen's for a new state and emits signal if needed

        Do not call. is called any time user or .setChecked(True/False) is performed
        :param state: state given by toggle signal
        :return: None
        """
        self.newStateSignal.emit(state)
        if state is False: #turn off
            self.setChecked(False)
            for cb in self.checkboxes:
                if cb.isChecked():
                    cb.newStateSignal.emit(False)  # Emits new checkstate of False if group is no longer selected
        else:  # state is true # turn on
            self.container.swapToGroup(self)
            for cb in self.checkboxes:
                if cb.getChecked():
                    cb.newStateSignal.emit(cb.isChecked())


class CurveCheckbox(qtw.QCheckBox):
    newStateSignal = qtc.pyqtSignal(bool)

    def __init__(self, name, container=None, group=None, curve=None):
        qtw.QCheckBox.__init__(self, name)
        self.name = name
        self.group = group
        self.groupbox = None
        self.container = container
        self.toggled.connect(self.newState)
        self.curve = curve

    def getGroup(self):
        return self.group

    def getChecked(self):
        box = self.groupbox
        if box is not None:
            if not box.getChecked():
                return False
        return self.isChecked()

    def newState(self, state):
        self.newStateSignal.emit(state)
        if state is True and self.groupbox is None:  # if switching to a new group
            self.container.swapToGroup(self)
