import math
from threading import RLock

import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as qtw
import Utils.Conversion as Conversion
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.Gauge import Gauge, DisplayGauge
from Framework.BaseClasses.QtMixin import DataWidget
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt5.QtGui import QBrush, QPen, QPainter
from Utils.QtUtils import toCartesian, drawPolygon

DGRAM_SIZE = 120

class PressureGauge(Gauge, DataWidget):
    def __init__(self, GUIInterface, name=None, label=None, parent=None, size=DGRAM_SIZE,
                 corrInputMin=0, corrInputMax=150, rawInputUnit="V", corrInputUnit="PSIA", corrOutputUnit="PSIA",
                 *args, **kwargs):
        DataWidget.__init__(self, GUIInterface=GUIInterface,name=name, label=label, parent=parent)
        Gauge.__init__(self, GUIInterface=GUIInterface, name=name, parent=parent, size=size,
                       corrInputMin=corrInputMin, corrInputMax=corrInputMax, rawInputUnit=rawInputUnit,
                       corrInputUnit=corrInputUnit, corrOutputUnit=corrOutputUnit,
                       *args, **kwargs)
        self.lock = RLock()
        absMin = Conversion.getAbsoluteMin(corrInputUnit)
        inputMin = min(absMin, corrInputMin)

        self.displayGauge = POutputGauge(min=inputMin, max=corrInputMax, unit=corrInputUnit, size=DGRAM_SIZE)
        self.displayGauge.changeValue(absMin)
        self.initMMD()
        self.initUOB()
        self.addToLayout()

class POutputGauge(DisplayGauge):
    def __init__(self, min, max, unit='PSIA', size=DGRAM_SIZE):
        qtw.QWidget.__init__(self)
        self.setGeometry(0, 0, size, size)
        self.setMinimumSize(size, size)
        self.setMaximumSize(size, size)
        self.length = size

        self.adaptiveColor = Qt.blue

        self.lowerAngle = -60
        self.upperAngle = 300

        self.minTick = 180 + self.lowerAngle
        self.maxTick = 120 + self.upperAngle

        self.center = QPointF(size/2.0, size/2.0)

        self.outerFrac = .95
        self.innerFrac = .8
        self.centerFrac = .075
        self.outerCorner = ((1.0 - self.outerFrac) * size / 2.0, (1.0 - self.outerFrac) * size / 2.0)
        self.innerCorner = ((1.0 - self.innerFrac) * size / 2.0, (1.0 - self.innerFrac) * size / 2.0)
        self.centerCorner = ((1.0 - self.centerFrac) * size / 2.0,(1.0 - self.centerFrac) * size / 2.0)

        self.outerBox = QRectF(*self.outerCorner, self.outerFrac * size, self.outerFrac * size)
        self.innerBox = QRectF(*self.innerCorner, self.innerFrac * size, self.innerFrac * size)
        self.centerBox = QRectF(*self.centerCorner, self.centerFrac * size, self.centerFrac * size)
        #input
        self.inputUnit = unit
        self.inputMin = min
        self.inputMax = max
        #display
        self.displayUnit = unit
        self.displayMin = min
        self.displayMax = max

        self.displayValue = min

        self.upperLeft = QPointF(0, 0)

        self.outerPen = QPen(Qt.gray)
        self.outerPen.setWidth(5)

        self.innerPen = QPen(Qt.black)
        self.innerPen.setWidth(2)
        self.fill = QBrush(Qt.white)
        self.centerFill = QBrush(Qt.black)
        self.noFill = QBrush()
        self.painter = QPainter()

    def paintEvent(self, QPaintEvent):
        self.painter.begin(self)
        self.painter.setPen(self.innerPen)
        self.painter.setPen(self.outerPen)
        self.painter.setBrush(self.fill)
        self.painter.drawEllipse(self.outerBox)

        self.painter.setPen(self.innerPen)

        for i in range(self.minTick, self.maxTick+1):
            if i % 5 == 0:
                self.drawTick(i, 15, angleInDegrees=True)
            if i % 60 == 0:
                percent = (i-self.minTick)/(self.maxTick-self.minTick)
                text = int(self.displayMin + percent*(self.displayMax-self.displayMin))
                self.drawTick(i, 30, angleInDegrees=True, text=text)
        if self.displayValue is not None:
            self.drawPointer()

        self.painter.drawArc(self.innerBox, self.lowerAngle*16, self.upperAngle*16)

        self.painter.setPen(self.innerPen)
        self.painter.setBrush(self.centerFill)
        self.painter.drawEllipse(self.centerBox)

        self.painter.end()

    def drawTick(self, angle, length, angleInDegrees = False, text=None):
        self.innerPen = QPen(Qt.darkGray)
        if angleInDegrees:
            angle = angle/180.0*math.pi
        outerPoint = QPointF(*[sum(x) for x in zip((self.length/2.0, self.length/2.0), toCartesian(self.length/2.0-self.innerCorner[0], angle))])
        innerPoint = QPointF(*[sum(x) for x in zip((self.length/2.0, self.length/2.0), toCartesian(self.length/2.0-(self.innerCorner[0] + .5*length), angle))])
        textPoint = QPointF(*[sum(x) for x in zip((self.length / 2.0, self.length / 2.0),
                                                   toCartesian(self.length / 1.6 - (self.innerCorner[0] + 1.3 * length),
                                                               angle))])
        brwidth = 30
        brheight = 20
        textPoint.setX(textPoint.x() - 1 / 2 * brwidth)
        textPoint.setY(textPoint.y() - 1 / 2 * brheight)
        size = QSizeF(brwidth, brheight)
        box = QRectF(textPoint, size)
        self.painter.drawLine(outerPoint, innerPoint)
        if text is not None:
            # self.painter.drawRect(box)
            font = ['Helvetica', 6, 50, False]
            qfont = QtGui.QFont(*font)
            self.painter.setFont(qfont)
            self.painter.drawText(box, Qt.TextDontClip | Qt.AlignCenter, "{0:g}".format(text))

    def drawPointer(self):
        minRotation = 30.0
        maxRotation = 330.0
        val = self.displayValue
        if val < self.displayMin:
            val = self.displayMin
        if val > self.displayMax:
            val = self.displayMax
        rotate = minRotation + (maxRotation-minRotation)*((val-self.displayMin)/(self.displayMax-self.displayMin))
        self.painter.setBrush(self.centerFill)
        point1 = (-(self.length/2.0-self.centerCorner[0]), 0)
        point2 = (self.length/2.0-self.centerCorner[0], 0)
        point3 = (0, self.length/2.0-self.innerCorner[0])
        drawPolygon(self.painter, [point1, point2, point3], 1, [self.length/2.0, self.length/2.0], rotate)
        self.painter.setBrush(self.noFill)

    def changeInputUnit(self, inputUnit):
        self.inputUnit = inputUnit

    def changeUnit(self, unit):
        self.displayUnit = unit
        self.changeValue(self.inputValue)

    def changeMinMax(self, newmin, newmax):
        self.displayMin = newmin
        self.displayMax = newmax
        if self.displayMin < 0:
            self.displayMin = 0
        if self.displayMax < 1:
            self.displayMax = 1
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

    def setAdaptiveColor(self, qcolor):
        self.adaptiveColor = qcolor