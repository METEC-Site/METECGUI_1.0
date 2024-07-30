import json
import os
import sys

import numpy as np
from Applications.METECControl.GUI.RefactoredWidgets.MET.RadialPainter import RadialPainter
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
from PyQt5 import QtWidgets as qtw

RADIUS = 200
BORDER_WIDTH = 15

DIR_BINS = [i/2 for i in range(0,360*2,45)]
ARCLENGTH = 360/len(DIR_BINS)
# ARCLENGTH = 19

ROSE_WIDTH = BORDER_WIDTH*2+RADIUS*2
ROSE_HEIGHT = ROSE_WIDTH


class RoseDirection:

    def __init__(self, direction, speedBins):
        self.direction = direction
        self.frequencyPercentage = 0
        self.speedCounts = {sBin:0 for sBin in speedBins}
        self.count = 0

    def increment(self):
        self.count+=1
        return self.count

    def incrementSpeed(self, speedBin):
        self.speedCounts[speedBin] += 1

    def getSpeedPercentages(self, speedBins):
        percents = []
        if self.count > 0:
            for speed in speedBins:
                percent = float(self.speedCounts[speed]/self.count)
                percents.append(percent)
        else:
            percents = [0]*len(speedBins)
        return percents

class WindRose(qtw.QWidget):

    def __init__(self, label=""):
        qtw.QWidget.__init__(self)
        self.speedBins = [0]
        self.colors = [qtc.Qt.gray]*6
        self.pen = None
        self.staticIndexes = (0, 0)
        self.setFixedSize(ROSE_WIDTH + 100, ROSE_HEIGHT + 30)
        self.label = label
        #context menu

        #loadconfig
        self.loadConfig()
        self.painter = qtg.QPainter()
        self.layout = qtw.QGridLayout()
        self.setLayout(self.layout)
        self.maxFreq = 0
        self.deg = np.empty(0)
        self.mag = np.empty(0)
        self.time = np.empty(0)
        self.numWind = 0
        self.rose = None  # dictionary of RoseDirections for each BIN
        self.maxSpeed = 0

    def loadConfig(self):
        try:
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "metDisplayConfig-user.json"),
                      "r") as f:
                config = json.load(f)
                self._setConfig(config)
        except:
            self.loadDefaultConfig()

    def loadDefaultConfig(self):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"metDisplayConfig-default.json"), "r") as f:
            config = json.load(f)
            self._setConfig(config)

    def _setConfig(self, config):
        colors = []
        speedBins = [0]
        for span in config:
            speedBins.append(span.get("span")[1])
            rgb = span.get("colorRGB").split(",")
            colors.append(qtg.QColor(int(rgb[0]), int(rgb[1]), int(rgb[2])))
        self.colors = colors
        self.speedBins = speedBins
        self.numberSpeedBins = len(config)
        self.config = config

    def setData(self, deg, mag, time):
        self.deg = deg
        self.mag = mag
        self.time = time
        self.rose = self.getRoseFromWindMeasurements(self.deg, self.mag, self.time)
        self.update()

    def paintEvent(self, QPaintEvent):
        self.painter.begin(self)
        self.pen = self.painter.pen()
        # STATIC
        self.painter.drawStaticText(0, 0, qtg.QStaticText(str(self.label)))
        # windrose circle and N S E W labels
        self.painter.drawStaticText(RADIUS+BORDER_WIDTH-10, BORDER_WIDTH-15, qtg.QStaticText("N / -U"))
        self.painter.drawStaticText(RADIUS+BORDER_WIDTH-20, RADIUS*2+BORDER_WIDTH, qtg.QStaticText("S / +U"))
        self.painter.drawStaticText(RADIUS*2+BORDER_WIDTH+3, RADIUS+BORDER_WIDTH-15, qtg.QStaticText("E"))
        self.painter.drawStaticText(RADIUS*2+BORDER_WIDTH+3, RADIUS+BORDER_WIDTH+5, qtg.QStaticText("V"))
        self.painter.drawStaticText(0, RADIUS+BORDER_WIDTH-15, qtg.QStaticText("W"))
        self.painter.drawStaticText(0, RADIUS+BORDER_WIDTH+5, qtg.QStaticText("-V"))
        self.painter.drawEllipse(BORDER_WIDTH, BORDER_WIDTH, RADIUS*2, RADIUS*2)
        # percentage bar on the bottom
        self.painter.drawLine(BORDER_WIDTH, ROSE_HEIGHT + 10, RADIUS + BORDER_WIDTH,
                              ROSE_HEIGHT + 10)  # horizontal line on bottom
        self.painter.drawLine(BORDER_WIDTH, BORDER_WIDTH * 2 + RADIUS * 2 + 10, BORDER_WIDTH,
                              BORDER_WIDTH * 2 + RADIUS * 2 - 30)  # leftmost vertical line
        self.painter.drawLine(BORDER_WIDTH + RADIUS / 2, BORDER_WIDTH * 2 + RADIUS * 2 + 10, BORDER_WIDTH + RADIUS / 2,
                              BORDER_WIDTH * 2 + RADIUS * 2 - 15)  # middle vertical line
        self.painter.drawLine(BORDER_WIDTH + RADIUS, BORDER_WIDTH * 2 + RADIUS * 2 + 10, BORDER_WIDTH + RADIUS,
                              BORDER_WIDTH * 2 + RADIUS * 2 + 5)  # 0% veritcal line
        self.painter.drawText(BORDER_WIDTH + RADIUS - 5, BORDER_WIDTH * 2 + RADIUS * 2 + 25, "0%")  # 0 percent text

        # dynamic
        try:
            if self.rose != None and len(self.colors) == len(self.speedBins)-1 != 0:
                for direction, roseDir in self.rose.items():
                    maxP = roseDir.frequencyPercentage
                    if roseDir.count > 0:
                        colorIndex = 0
                        lastSpeedP = 0
                        speedPercentages = roseDir.getSpeedPercentages(self.speedBins)
                        for speedP in speedPercentages:
                            if speedP > 0:
                                RadialPainter.drawPartialSlice(self.painter, BORDER_WIDTH+RADIUS, BORDER_WIDTH+RADIUS, RADIUS, direction, ARCLENGTH, maxP*lastSpeedP, maxP*(speedP+lastSpeedP), self.colors[colorIndex])
                                lastSpeedP = speedP+lastSpeedP
                            colorIndex+=1
                ###### percentage bar
                counts = [roseDir.count for roseDir in self.rose.values()]
                if len(counts) > 0:
                    maxPercent = max(counts)*100/sum(counts)
                    self.painter.drawText(BORDER_WIDTH-5,BORDER_WIDTH*2+RADIUS*2+25, str(round(maxPercent))+"%")  # maxpercent text
                    self.painter.drawText(BORDER_WIDTH+RADIUS/2-5,BORDER_WIDTH*2+RADIUS*2+25, str(round(maxPercent/2))+"%")  # middle percent text
                ###### color legend
                bottomStart = ROSE_WIDTH+BORDER_WIDTH
                stepCount = 0
                for span in self.config:
                    start,stop = span.get('span')
                    height = round((stop-start)*ROSE_WIDTH)
                    self.painter.fillRect(ROSE_WIDTH+5, bottomStart-round(start*ROSE_WIDTH), 10, -height, self.colors[stepCount])
                    self.painter.drawText(ROSE_WIDTH+15, bottomStart-round(start*ROSE_WIDTH), str(round(self.speedBins[stepCount], 1))+" m/s")
                    stepCount+=1
                self.painter.drawText(ROSE_WIDTH+15, 10, str(round(self.maxSpeed))+" m/s")
        except Exception as e:
            print("Error in painting wind rose:", e)

        ##### Paint semi-transparent inner circles
        pencolor = self.pen.color()
        pencolor.setAlphaF(.3)
        transparentpen = qtg.QPen(pencolor)
        self.painter.setPen(transparentpen)
        self.painter.drawEllipse(BORDER_WIDTH+RADIUS/2, BORDER_WIDTH+RADIUS/2, RADIUS, RADIUS)
        self.painter.drawEllipse(BORDER_WIDTH+RADIUS/4, BORDER_WIDTH+RADIUS/4, RADIUS*3/2, RADIUS*3/2)
        self.painter.drawEllipse(BORDER_WIDTH+RADIUS*3/4, BORDER_WIDTH+RADIUS*3/4, RADIUS/2, RADIUS/2)
        self.painter.drawLine(BORDER_WIDTH, RADIUS+BORDER_WIDTH, RADIUS*2+BORDER_WIDTH, RADIUS+BORDER_WIDTH)
        self.painter.drawLine(BORDER_WIDTH+RADIUS, BORDER_WIDTH, RADIUS+BORDER_WIDTH, RADIUS*2+BORDER_WIDTH)
        self.painter.setPen(self.pen)
        self.painter.end()

    def getRoseFromWindMeasurements(self, degrees, magnitudes, time):
        if len(time)>0:
            self.maxSpeed = max(magnitudes)
            self.maxFreq = 0  # largest quantity of wind measurements in one direction out of all wind directions
            self.speedBins = self.generateSpeedBins(self.maxSpeed)  # calculate speed bin ranges for each color based on maximum speed
            rose = {direction: RoseDirection(direction, self.speedBins) for direction in DIR_BINS}  # create roseDirection object for each direction
            for i in range(len(degrees)):
                dir = self.getDirectionBin(degrees[i])
                count = rose[dir].increment()
                self.maxFreq = max(self.maxFreq, count)
                rose[dir].incrementSpeed(self.getSpeedBin(magnitudes[i]))
            for roseDir in rose.values():
                roseDir.frequencyPercentage = roseDir.count/self.maxFreq
            return rose
        else:
            return None


    def generateSpeedBins(self, maxSpeed):
        bins = [0]
        for span in self.config:
            bins.append(span.get("span")[1]*maxSpeed)
        return bins

    def getSpeedBin(self, speed):
        for b in range(1,len(self.speedBins)):
            if speed <= self.speedBins[b]:
                return self.speedBins[b-1]
        return self.speedBins[-1]

    def getDirectionBin(self, direction):
        for i in range(len(DIR_BINS)):
            if abs(DIR_BINS[i]-direction%360) <= 11.25:
                return DIR_BINS[i]
        return 0

    def getRangeForTime(self, start, end):
        istart = None
        iend = None
        # if start==end:
        #     return (0,0)
        for i in range(len(self.time)):
            if not istart and self.time[i] > start:
                istart = i
            if not iend and self.time[i] > end:
                iend = i
                break
        if iend is None:
            iend = len(self.time)
        return (istart, iend)



def displayRose(label, degrees, magnitudes, timesEpoch):
    app = qtw.QApplication(sys.argv)
    wr = WindRose(label)
    # wr.setGeometry(1000,1000,1000,1000)
    wr.setData(degrees, magnitudes, timesEpoch)
    wr.show()
    app.exec()

def saveRoseFile(degrees, magnitudes, timesEpoch):
    app = qtw.QApplication(sys.argv)
    wr = WindRose("test")
    wr.setData(degrees, magnitudes, timesEpoch)


if __name__ == '__main__':
    displayRose([10, 20, 34], [5,6,7], [1,2,3])