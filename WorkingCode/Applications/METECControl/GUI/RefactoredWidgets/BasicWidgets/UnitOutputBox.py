import logging
from threading import RLock

import PyQt5.QtCore as qtc
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as qtw
import Utils.Conversion as convert
from Framework.BaseClasses.QtMixin import QtMixin


class UnitOutputBox(qtw.QWidget, QtMixin):

    unitChanged = qtc.pyqtSignal(str)

    def __init__(self, GUIInterface, name=None, parent=None, units='units', unitDict={}, *args, **kwargs):
        QtMixin.__init__(self, GUIInterface, name, parent, *args, **kwargs)
        qtw.QWidget.__init__(self, parent=parent)

        self.gridLayout = qtw.QGridLayout()
        self.setLayout(self.gridLayout)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setSpacing(0)

        sizePolicy = qtw.QSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)
        # self.setFixedWidth(110)
        self.setSizePolicy(sizePolicy)
        font = kwargs.get('font', ['Helvetica', 11, 50, False])
        self.valueBox = qtw.QLabel(self)
        qfont = QtGui.QFont(*font)
        self.valueBox.setFont(qfont)
        self.valueBox.adjustSize()
        self.valueBox.setSizePolicy(sizePolicy)
        self.valueBox.setFrameShape(qtw.QFrame.Box)
        self.valueBox.setFrameShadow(qtw.QFrame.Raised)
        self.valueBox.setAlignment(qtc.Qt.AlignVCenter | qtc.Qt.AlignRight)
        self.gridLayout.addWidget(self.valueBox, 0, 0)
        self.valueBoxWidth = self.valueBox.width()

        # todo: pick from here, mandating that UOB's are given their units by the parent.


        self.inputUnit = units
        self.displayUnit = self.inputUnit

        self.unitBox = qtw.QComboBox(self)
        self.unitBox.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)
        self.unitBox.wheelEvent = lambda ev: ev.ignore()  # stops unitboxes from messing with scrollarea
        self.unitBox.setFont(qfont)
        self.unitDict = unitDict
        if self.unitDict:
            for singleUnitField in self.unitDict.values():
                self.unitBox.addItem(singleUnitField.get('abbr'))
        if not self.unitDict:
            logging.debug("No dictionary of available units given to Outputbox")
        self.unitBox.setCurrentIndex(self.unitBox.findText(self.displayUnit))
        self.unitBox.currentTextChanged.connect(self.changeUnitAndSignal)
        self.gridLayout.addWidget(self.unitBox, 0, 1)
        self.lock = RLock()

    def update(self):
        qtw.QWidget.update(self)

    def setInputUnit(self, inputUnit):
        self.inputUnit = inputUnit

    def changeValue(self, inputValue):
        with self.lock:
            if inputValue is None:  # allows null input value
                self.valueBox.setText("Null")
            else:
                if self.displayUnit != self.inputUnit:
                    outputValue = convert.convert(inputValue, self.inputUnit, self.displayUnit)
                else:
                    outputValue = inputValue
                # todo: look into getting maximum data precision from sensor properties
                lenDec = 0
                absValue = abs(inputValue)
                if absValue < 10000:
                    lenDec = 1
                if absValue < 100:
                    lenDec = 2
                if absValue < 10:
                    lenDec = 3
                self.valueBox.setText(format(outputValue, "."+str(lenDec)+"f"))

            # label width fixing
            curWidth = self.valueBox.width()
            if curWidth > self.valueBoxWidth:
                self.valueBoxWidth = curWidth
                self.valueBox.setMinimumWidth(curWidth)
                self.valueBox.adjustSize()

            self.update()

    def changeUnitAndSignal(self, unitAbbr): # used by combobox currentTextChange Signal
        # unit is the abbr of the unit as per the dictionary in conversion utils.
        with self.lock:
            self.changeUnit(unitAbbr)
            self.unitChanged.emit(unitAbbr)

    def changeUnit(self, unitAbbr):  # used when another object wants to change this unit
        with self.lock:
            self.displayUnit = unitAbbr
            if self.unitBox.currentIndex() == self.unitBox.findText(unitAbbr):
                pass
            else:
                self.unitBox.setCurrentIndex(self.unitBox.findText(unitAbbr))

    def getDisplayUnit(self):
        return self.displayUnit

    def getInputUnit(self):
        return self.inputUnit
