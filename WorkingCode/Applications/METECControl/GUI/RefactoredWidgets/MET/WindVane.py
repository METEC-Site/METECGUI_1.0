from Applications.METECControl.GUI.RefactoredWidgets.MET.RadialPainter import RadialPainter
from Framework.BaseClasses.QtMixin import QtMixin
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
from PyQt5 import QtWidgets as qtw
from Utils.Conversion import uvFromDegMag

RADIUS = 100
BORDER_WIDTH = 15
PAINT_EDGE = RADIUS*2+BORDER_WIDTH*2

class WindVane(qtw.QWidget, QtMixin):

    def __init__(self, GUIInterface, name=None, parent=None, *args, **kwargs):
        QtMixin.__init__(self, GUIInterface=GUIInterface, name=name, parent=parent, *args, **kwargs)
        qtw.QWidget.__init__(self, parent=parent)
        self.direction=0
        self.painter = qtg.QPainter()
        self.pen = self.painter.pen()
        self.layout = qtw.QGridLayout()
        # self.layout.setSizeConstraint(qtc.Qt.Size)
        self.setLayout(self.layout)
        self.infoLabel = qtw.QLabel("Speed:\nDirection:\nU:\nV:\nW:")
        self.infoOut = qtw.QLabel("0\n0\n0\n0\n0")
        self.layout.addItem(qtw.QSpacerItem(PAINT_EDGE, PAINT_EDGE), 1, 1)
        self.layout.addWidget(self.infoLabel, 2, 1)
        self.layout.addWidget(self.infoOut, 2, 2)
        self.layout.addItem(qtw.QSpacerItem(80, 30), 2, 3)
        self.setFixedSize(PAINT_EDGE+40, 130+ PAINT_EDGE)

    def update(self):
        qtw.QWidget.update(self)

    def setData(self, degree, magnitude):
        u, v = uvFromDegMag(degree, magnitude)
        self.updateInfoOut(u, v, 0, degree, magnitude)
        self.direction = degree
        self.update()

    def updateInfoOut(self, u, v, w, deg, mag):
        self.infoOut.setText(f"{round(mag, 2)} m/s\n{round(deg, 2)}°\n{round(u, 2)}\n{round(v, 2)}\n{round(w, 2)}")

    def paintEvent(self, QPaintEvent):
        self.painter.begin(self)
        # static
        self.painter.drawEllipse(BORDER_WIDTH, BORDER_WIDTH, RADIUS * 2, RADIUS * 2)
        self.painter.drawStaticText(RADIUS + BORDER_WIDTH - 20, 0, qtg.QStaticText("N / -U"))
        self.painter.drawStaticText(RADIUS + BORDER_WIDTH - 20, RADIUS * 2 + BORDER_WIDTH + 5,
                                    qtg.QStaticText("S / +U"))
        self.painter.drawStaticText(RADIUS * 2 + BORDER_WIDTH + 3, RADIUS / 2 + BORDER_WIDTH * 3 + 5,
                                    qtg.QStaticText("E"))
        self.painter.drawStaticText(RADIUS * 2 + BORDER_WIDTH + 3, RADIUS / 2 + BORDER_WIDTH * 3 + 20,
                                    qtg.QStaticText("V"))
        self.painter.drawStaticText(0, RADIUS / 2 + BORDER_WIDTH * 3 + 5, qtg.QStaticText("W"))
        self.painter.drawStaticText(0, RADIUS / 2 + BORDER_WIDTH * 3 + 20, qtg.QStaticText("-V"))
        pencolor = self.pen.color()
        pencolor.setAlphaF(.3)
        transparentpen = qtg.QPen(pencolor)
        self.painter.setPen(transparentpen)
        self.painter.drawLine(BORDER_WIDTH, RADIUS + BORDER_WIDTH, RADIUS * 2 + BORDER_WIDTH, RADIUS + BORDER_WIDTH)
        self.painter.drawLine(BORDER_WIDTH + RADIUS, BORDER_WIDTH, RADIUS + BORDER_WIDTH, RADIUS * 2 + BORDER_WIDTH)
        self.painter.setPen(self.pen)
        # dynamic
        RadialPainter.drawLine(self.painter, BORDER_WIDTH + RADIUS, BORDER_WIDTH + RADIUS, RADIUS, self.direction,
                               1)
        RadialPainter.drawSlice(self.painter, BORDER_WIDTH + RADIUS, BORDER_WIDTH + RADIUS, RADIUS, self.direction,
                                45, .2, qtc.Qt.black)
        self.painter.end()