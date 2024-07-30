import math

import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg
from PyQt5 import Qt


class RadialPainter:


    @staticmethod
    def drawLine(painter:qtg.QPainter, center_x, center_y, radius, degrees, lengthRatio=1):
        radians = math.radians(-degrees)
        painter.drawLine(center_x, center_y, center_x + radius * math.cos(math.pi / 2 + radians) * lengthRatio,
                         center_y - radius * math.sin(math.pi / 2 + radians)*lengthRatio)

    @staticmethod
    def drawSlice(painter:qtg.QPainter, center_x, center_y, radius, degreeCenter, arcLength, lengthRatio=1, color=qtc.Qt.black):
        leftRadians = math.radians(-(degreeCenter-(arcLength/2)))
        rightRadians = math.radians(-(degreeCenter+(arcLength/2)))
        points = qtg.QPolygon()
        points.append(Qt.QPoint(center_x, center_y))
        leftX = center_x + radius * math.cos(math.pi / 2 + leftRadians) * lengthRatio
        leftY = center_y - radius * math.sin(math.pi / 2 + leftRadians) * lengthRatio
        points.append(Qt.QPoint(leftX, leftY))
        rightX = center_x + radius * math.cos(math.pi / 2 + rightRadians) * lengthRatio
        rightY = center_y - radius * math.sin(math.pi / 2 + rightRadians) * lengthRatio
        points.append(Qt.QPoint(rightX, rightY))
        points.append(Qt.QPoint(center_x, center_y))
        oldbrush = painter.brush()
        brush = qtg.QBrush(color, qtc.Qt.SolidPattern)
        painter.setBrush(brush)
        painter.drawPolygon(points)
        painter.setBrush(oldbrush)

    @staticmethod
    def drawPartialSlice(painter: qtg.QPainter, center_x, center_y, radius, degreeCenter, arcLength, startLength=0, endLength=1, color=qtc.Qt.black):
        leftRadians = math.radians(-(degreeCenter - (arcLength / 2)))
        rightRadians = math.radians(-(degreeCenter + (arcLength / 2)))
        points = qtg.QPolygonF()
        # bottom
        bottomRight = (center_x + radius * math.cos(math.pi / 2 + rightRadians) * startLength,
                       center_y - radius * math.sin(math.pi / 2 + rightRadians) * startLength)
        points.append(Qt.QPoint(*bottomRight))
        bottomLeft = (center_x + radius * math.cos(math.pi / 2 + leftRadians) * startLength,
                      center_y - radius * math.sin(math.pi / 2 + leftRadians) * startLength)
        points.append(Qt.QPoint(*bottomLeft))
        # top
        topLeft = (center_x + radius * math.cos(math.pi / 2 + leftRadians) * endLength,
                   center_y - radius * math.sin(math.pi / 2 + leftRadians) * endLength)
        points.append(Qt.QPoint(*topLeft))
        topRight = (center_x + radius * math.cos(math.pi / 2 + rightRadians) * endLength,
                    center_y - radius * math.sin(math.pi / 2 + rightRadians) * endLength)
        points.append(Qt.QPoint(*topRight))
        points.append(Qt.QPoint(*bottomRight)) # return to start
        oldbrush = painter.brush()
        brush = qtg.QBrush(color, qtc.Qt.SolidPattern)
        painter.setBrush(brush)
        painter.drawPolygon(points)
        painter.setBrush(oldbrush)