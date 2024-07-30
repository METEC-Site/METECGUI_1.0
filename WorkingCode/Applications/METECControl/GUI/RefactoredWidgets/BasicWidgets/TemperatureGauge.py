# Q progress bar vertical orientation
import os

import PyQt5.QtWidgets as qtw
import Utils.Conversion as Conversion
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.Gauge import Gauge, DisplayGauge
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt

"""
.. _temp-gauge-module:

#################
Temperature Gauge
#################

:Authors: Aidan Duggan, Jerry Duggan
:Date: April 30, 2019

This module provides the Temperature Gauge widget.
"""
__docformat__ = 'reStructuredText'

DGRAM_SIZE = 100


class TemperatureGauge(Gauge):
    """
    .. _temperature-gauge-widget:

    Temperature Gauge Widget:

    - Displays *value* between bounds *min* and *max*.
    - creates new TemperatureGauge based on config json file
    """
    def __init__(self, GUIInterface, name=None, parent=None,
                 corrInputMin=-20, corrInputMax=120, rawInputUnit="V", corrInputUnit="F", corrOutputUnit="F",
                 *args, **kwargs):

        Gauge.__init__(self, GUIInterface, name=name, parent=parent,
                       corrInputMin=corrInputMin, corrInputMax=corrInputMax, rawInputUnit=rawInputUnit,
                       corrInputUnit=corrInputUnit, corrOutputUnit=corrOutputUnit,
                       *args, **kwargs)

        self.displayGauge = TOutputGauge(self.name, corrInputMin, corrInputMax, corrInputUnit)
        self.displayGauge.changeValue(corrInputMin)

        self.initMMD()
        self.initUOB()
        self.addToLayout()

# Constants for thermometer painting
OFFSET = 30
TEMP_TOP = 15
TEMP_BOTTOM = 130
TEMP_LENGTH = TEMP_BOTTOM-TEMP_TOP
CENTER_BULB = 160
BULB_LEFT = -25
TEMP_LEFT = -15
TEMP_RIGHT = 15

class TOutputGauge(DisplayGauge):

    def __init__(self, name, inputMin=-20, inputMax=120, inputUnit="F", size=DGRAM_SIZE):
        qtw.QWidget.__init__(self)
        self.name = name
        self.displayValue = inputMin
        self.inputValue = inputMin
        # display values
        self.displayUnit = inputUnit
        self.displayMin = inputMin
        self.displayMax = inputMax

        self.inputUnit = inputUnit
        self.inputMin = inputMin
        self.inputMax = inputMax

        self.adaptiveColor = Qt.blue
        self.painter = QtGui.QPainter()

        self.numberTicks = 17
        self.numberNums = int(self.numberTicks/4+1)
        self.minFont = 15
        xFactor = .8
        width = int(xFactor * size)
        self.setGeometry(0, 0, width, size)
        self.setMinimumSize(width, size)
        self.setMaximumSize(width, size)

        self.thermPath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'resources/thermometer.svg'))
        self.thermIcon = QtGui.QIcon(self.thermPath)
        self.thermIcon = self.thermIcon.pixmap(QtCore.QSize(2000, 2000))

    def paintEvent(self, event):
        self.updateAdaptiveColor()
        self.painter.begin(self)
        self.initDrawing(self.painter)
        self.drawBackground(self.painter)
        if self.displayValue is not None:
            self.drawTemperature(self.painter)
        self.drawTicks(self.painter)
        self.drawNumber(self.painter)
        self.painter.end()

    def drawBackground(self, painter):
        painter.drawPixmap(-100, 0, 200, 200, self.thermIcon)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self.adaptiveColor)
        painter.drawEllipse(BULB_LEFT, TEMP_BOTTOM + 4, -(BULB_LEFT * 2), -(BULB_LEFT * 2))
        painter.setBrush(QtGui.QBrush())

    def initDrawing(self, painter):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.translate(self.width() / 2.0, 0.0)
        painter.scale(self.height() / 200.0, self.height() / 200.0)

    def drawTicks(self, painter):
        pen = QtGui.QPen()
        painter.drawLine(TEMP_LEFT, TEMP_TOP, TEMP_RIGHT, TEMP_TOP + TEMP_LENGTH)
        spacer = (TEMP_LENGTH / (self.numberTicks - 1))
        for i in range(self.numberTicks):
            length = 20
            pen.setWidthF(1)
            if i % 4 != 0:
                length = 12
                pen.setWidthF(0.6)
            if i % 2 != 0:
                length = 8
                pen.setWidthF(0.4)
            painter.setPen(pen)
            painter.drawLine(int(TEMP_RIGHT - length), int(TEMP_BOTTOM - (i * spacer)), int(TEMP_RIGHT), int(TEMP_BOTTOM - (i * spacer)))

    def drawNumber(self, painter):
        for i in range(self.numberNums):
            numDelta = (self.displayMax-self.displayMin)/(self.numberNums-1)
            numPixDelta = TEMP_LENGTH/(self.numberNums-1)
            if numDelta<10:
                num = float(i*numDelta+self.displayMin)
            else:
                num = int(round(i*numDelta+self.displayMin))

            val = "{0}".format(num)
            # f = painter.fontInfo().pointSize
            font = painter.font()
            font.setPointSize(self.minFont)
            painter.setFont(font)
            fm = painter.fontMetrics()
            size = fm.size(QtCore.Qt.TextSingleLine, val)
            point = QtCore.QPointF(OFFSET, TEMP_BOTTOM - (i * numPixDelta) + size.width() / 4)
            painter.drawText(point, val)

    def drawTemperature(self, painter):
        factor = self.displayValue - self.displayMin
        factor = (factor / (self.displayMax - self.displayMin))
        tempPIX = (TEMP_LENGTH) * factor
        height = int(TEMP_BOTTOM - CENTER_BULB - tempPIX)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self.adaptiveColor)
        painter.drawRect(TEMP_LEFT, CENTER_BULB, TEMP_RIGHT - TEMP_LEFT, height)

    def changeInputUnit(self, inputUnit):
        self.inputUnit = inputUnit

    def changeUnit(self, unit):
        self.displayUnit = unit
        self.changeValue(self.inputValue)

    def changeMinMax(self, newmin, newmax):
        self.displayMin = newmin
        self.displayMax = newmax
        self.changeValue(self.inputValue)

    def changeValue(self, val):
        self.inputValue = val
        if val is None:
            self.displayValue = self.displayMin
            return
        if self.displayUnit != self.inputUnit:
            val = Conversion.convert(self.inputValue, self.inputUnit, self.displayUnit)

        if val < self.displayMin:
            self.displayValue = self.displayMin
        elif val > self.displayMax:
            self.displayValue = self.displayMax
        else:
            self.displayValue = val

    def setAdaptiveColor(self, color):
        self.adaptiveColor = color

    def updateAdaptiveColor(self):
        if self.displayValue is None:
            return
        pmax = self.displayMax
        pvalue = max(self.displayValue, self.displayMin)
        pvalue = min(pvalue, self.displayMax)
        if pmax == 0:
            pmax = 1
        percent = float((pvalue-self.displayMin)/(pmax-self.displayMin))
        h = int(percent * (360-250)+250)
        qcolor = QtGui.QColor(0, 0, 255)
        qcolor.setHsl(h, 230, 100)
        self.adaptiveColor = qcolor
        self.setAdaptiveColor(self.adaptiveColor)
