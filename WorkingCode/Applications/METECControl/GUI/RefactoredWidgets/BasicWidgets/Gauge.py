# Q progress bar vertical orientation

from abc import abstractmethod

import PyQt5.QtWidgets as qtw
import Utils.Conversion as Conversion
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.Modes import InputMode
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.UnitOutputBox import UnitOutputBox
from Applications.METECControl.GUI.RefactoredWidgets.Menus.MinMaxDialogBox import MinMaxDialog
from Applications.METECControl.GUI.RefactoredWidgets.Menus.SensorPropertiesMenu import SensorPropertiesMenu
from Framework.BaseClasses.QtMixin import QtMixin, DataWidget
from PyQt5.QtCore import Qt

"""
.. _gauge-module:

#################
Gauge
#################

:Authors: Aidan Duggan, Jerry Duggan
:Date: April 30, 2019

This module provides the parent gauge widget for temperature and pressure gauges.
"""
__docformat__ = 'reStructuredText'

class DisplayGauge(qtw.QWidget, QtMixin):
    @abstractmethod
    def changeValue(self, val):
        pass

    @abstractmethod
    def changeMinMax(self, newmin, newmax):
        pass

    @abstractmethod
    def changeUnit(self, unit):
        pass

    @abstractmethod
    def setAdaptiveColor(self, qcolor):
        pass

class Gauge(qtw.QWidget, DataWidget):
    def __init__(self, GUIInterface, name=None, label=None, parent=None, corrInputMin=None, corrInputMax=None, rawInputUnit=None, corrInputUnit=None, corrOutputUnit=None,
                 sensorProperties=None,
                 *args, **kwargs):
        QtMixin.__init__(self, GUIInterface, name=name, parent=parent, *args, **kwargs)
        DataWidget.__init__(self, GUIInterface, name=name, label=label, parent=parent)
        qtw.QWidget.__init__(self, parent)
        self.setSizePolicy(qtw.QSizePolicy(qtw.QSizePolicy.Fixed, qtw.QSizePolicy.Minimum))
        self.sensorProperties = sensorProperties if not sensorProperties is None else {}

        self.corrValue = corrInputMin

        self.adaptiveColor = Qt.blue
        self.mode = InputMode.corrected

        self.rawInputUnit = rawInputUnit
        self.corrInputUnit = corrInputUnit
        self.corrOutputUnit = corrOutputUnit if corrOutputUnit else self.corrInputUnit

        # display values
        self.corrInputMin = corrInputMin # will always be the original min/max from config
        self.corrInputMax = corrInputMax # ^^

        self.displayMin = self.corrInputMin
        self.displayMax = self.corrInputMax
        self.absoluteMin = self.corrInputMin

        self.defaultMin = self.corrInputMin
        self.defaultMax = self.corrInputMax

        self.IDBox = qtw.QLabel(self.label)
        self.IDBox.setMaximumHeight(20)
        self.IDBox.setContentsMargins(0, 0, 0, 0)
        self.IDBox.setAlignment(Qt.AlignCenter | Qt.AlignBottom)

        self.mmd = None
        self.menu = None

        self.layout = qtw.QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignBottom)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # child init must check for None in all min/max/unit/value variables and set to default if None

    def initMMD(self):
        self.mmd = MinMaxDialog(self, self.corrOutputUnit, self.corrInputUnit, self.displayMin, self.displayMax)
        self.mmd.minmaxchanged.connect(self.changeMinMax)
        self.mmd.minmaxdefault.connect(self.resetMinMax)

    def initUOB(self):
        self.unitType, self.unitDict = Conversion.getDict(self.corrInputUnit)
        # if self.rawInputUnit:
        #     self.rawUnitType, self.rawUnitDict = Conversion.getDict(self.rawInputUnit)
        #     for key, val  in self.rawUnitDict.items():
        #         self.unitDict[key] = val
        self.unitBox = UnitOutputBox(self.GUIInterface, f'{self.name}UnitOutputBox', self, self.corrOutputUnit, unitDict=self.unitDict)
        self.unitBox.unitChanged.connect(self.changeUnit)
        self.unitBox.changeValue(None)

    def addToLayout(self):
        self.setFixedWidth(self.displayGauge.width()+25)
        self.absoluteMin = Conversion.getAbsoluteMin(self.corrOutputUnit)
        self.layout.addWidget(self.displayGauge, 2, Qt.AlignCenter)
        self.layout.addWidget(self.IDBox, 0, Qt.AlignCenter)
        self.layout.addWidget(self.unitBox, 0, Qt.AlignCenter)

    def update(self):
        qtw.QWidget.update(self)
        self.setCorrValue()
        self.unitBox.update()
        self.displayGauge.update()
        # if self.menu:
            # self.menu.sensprop.updateData({self.rawUnit: self.rawValue})
            # self.menu.update()

    def setRawValue(self, rawFieldname=None, rawValue=None):
        if self.menu:
            self.menu.sensprop.updateData({"Raw Value": format(rawValue, ".3f")})

    def setCorrValue(self, corrFieldname=None, corrValue=None):  # sets child values to current display value
        if corrValue is None:
            corrValue = self.corrValue
        self.corrValue = corrValue
        self.unitBox.changeValue(corrValue)
        self.displayGauge.changeValue(corrValue)

    def contextMenuEvent(self, ev):
        if not self.menu:
            self.menu = qtw.QMenu()
            self.menu.changeminmax = qtw.QAction("Change Min/Max")
            self.menu.changeminmax.triggered.connect(self.changeMinMaxContextMenu)
            self.menu.addAction(self.menu.changeminmax)
            self.menu.sensprop = SensorPropertiesMenu(self.GUIInterface, "SensorProperties", parent=self.menu, sensorproperties=self.sensorProperties)
            self.menu.sensprop.addData({"Raw Value": "NA"})
            self.menu.addMenu(self.menu.sensprop)
        self.menu.popup(ev.globalPos())

    def changeMinMaxContextMenu(self, event):
        self.mmd.show()

    def changeUnit(self, unit):
        self.corrOutputUnit = unit
        self.absoluteMin = Conversion.getAbsoluteMin(self.corrOutputUnit)
        self.changeMinMax(self.corrInputMin, self.corrInputMax, self.corrInputUnit)
        self.displayGauge.changeUnit(unit)
        self.unitBox.changeUnit(unit)
        self.update()

    def changeMinMax(self, newmin, newmax, fromUnit=None):
        displayUnit = self.unitBox.getDisplayUnit()
        if fromUnit is None:
            fromUnit = self.corrInputUnit
        self.corrInputMin = Conversion.convert(newmin, fromUnit, self.corrInputUnit)
        self.corrInputMax = Conversion.convert(newmax, fromUnit, self.corrInputUnit)
        if self.corrInputUnit == self.corrInputUnit:
            self.displayMin = Conversion.convert(self.corrInputMin, self.corrInputUnit, displayUnit)  # set min and max to correct value
            self.displayMax = Conversion.convert(self.corrInputMax, self.corrInputUnit, displayUnit)  # ...based on given
        else:
            pass
        self.displayMin = round(self.displayMin, 2)
        self.displayMax = round(self.displayMax, 2)
        self.displayGauge.changeMinMax(self.displayMin, self.displayMax)
        self.update()

    def resetMinMax(self):
        self.corrInputMin = self.defaultMin
        self.corrInputMax = self.defaultMax
        self.changeMinMax(self.corrInputMin, self.corrInputMax, self.corrInputUnit)
        self.update()