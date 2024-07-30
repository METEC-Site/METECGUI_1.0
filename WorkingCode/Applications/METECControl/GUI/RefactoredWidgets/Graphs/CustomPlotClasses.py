import PyQt5.QtCore as qtc
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as qtw
import pyqtgraph as pg
from Utils import Conversion
from Utils import TimeUtils as tu
from pyqtgraph import ViewBox

THIS_TIMEZONE = "US/Mountain"

class CustomPlot(pg.PlotWidget):

    createNote = qtc.pyqtSignal(dict)

    def __init__(self, parent=None, enableMenu=False, **kwargs):
        self.name = kwargs['title']
        pg.PlotWidget.__init__(self, parent, title=kwargs['title'], axisItems=kwargs['axisItems'], enableMenu=enableMenu)
        self.parent = parent
        self.menu = None

        self.leftAxis= self.plotItem
        self.leftVB = self.leftAxis.vb
        self.leftAxis.setLabels(left='Left Axis')
        # self.leftAxis.addLegend()

        # dual axis
        self.rightAxis = pg.ViewBox()
        self.leftAxis.showAxis('right')
        self.leftAxis.scene().addItem(self.rightAxis)
        self.leftAxis.getAxis('right').linkToView(self.rightAxis)
        self.rightAxis.setXLink(self.leftAxis)
        self.leftAxis.getAxis('right').setLabel('Right Axis', color='#ffffff')
        self.rightAxis.mouseClickEvent = self.raiseRightMenu
        self.leftAxis.vb.mouseClickEvent = self.raiseLeftMenu

        self.leftAxis.vb.sigResized.connect(self.updateViews)

        #mouse coordinates
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMovedPosition)
        self.mousePositionLabelLeft = pg.LabelItem(parent=self.leftAxis, size='9pt', justify="left", color="#ffffff")


        # self.leftAxis.vb.setLimits(xMin=tu.MIN_EPOCH, xMax=tu.MAX_EPOCH)
        # self.rightAxis.setLimits(xMin=tu.MIN_EPOCH, xMax=tu.MAX_EPOCH)

        self.xGraphController = GraphController(ViewBox.XAxis)
        self.xGraphController.graphWidthSignal.connect(self.setGraphWidth)
        self.xGraphController.graphRangeSignal.connect(lambda x, y: self.setGraphRange(x, y, ViewBox.XAxis))
        self.xGraphController.graphSeeAllSignal.connect(lambda x: self.setSeeAll(ViewBox.XAxis))
        # self.xGraphController.hideMenuSignal.connect(lambda: self.xGraphController.close())

        self.yGraphController = GraphController(ViewBox.YAxis)
        self.yGraphController.graphWidthSignal.connect(self.setGraphWidth)
        self.yGraphController.graphRangeSignal.connect(lambda x, y: self.setGraphRange(x, y, ViewBox.YAxis))
        self.yGraphController.graphSeeAllSignal.connect(lambda x: self.setSeeAll(ViewBox.YAxis))
        # self.yGraphController.hideMenuSignal.connect(lambda x: self.yGraphController.close())

        self.graphScroll = True # default to scrolling initially
        self.graphWidth = 300  # x scrolling width (seconds)

        self.lineLabels = []

        self.infLine = pg.InfiniteLine(angle=90, pos=tu.nowEpoch(), movable=True)
        self.infLineLabel = pg.InfLineLabel(self.infLine, "", position=.9, anchor=(0, 0), rotateAxis=(0, -1))
        self.infLine.visible = False
        self.lineLabels.append((self.infLine, self.infLineLabel))

        self.region = pg.LinearRegionItem()
        label1 = pg.InfLineLabel(self.region.lines[0], "", position=0.8, anchor=(0, 0), rotateAxis=(1, 0))
        label2 = pg.InfLineLabel(self.region.lines[1], "", position=0.8, anchor=(0, 0), rotateAxis=(1, 0))
        self.regLabels = (label1, label2)
        self.region.visible = False
        self.lineLabels.append((self.region.lines[0], label1))
        self.lineLabels.append((self.region.lines[1], label2))

        self.averagesLeft = []
        self.averagesRight = []

    def update(self):
        if self.graphScroll:
            self.setXRange(tu.nowEpoch()-self.graphWidth, tu.nowEpoch())
        for line, label in self.lineLabels:
            label.setText(qtc.QDateTime.fromSecsSinceEpoch(int(line.value())).toString("HH:mm:ss"))  # "MM-dd HH:mm:ss"

    def updateViews(self):
        # pg.GraphicsView(self).setGeometry
        self.rightAxis.setGeometry(self.leftAxis.vb.sceneBoundingRect())
        self.rightAxis.linkedViewChanged(self.leftAxis.vb, self.rightAxis.XAxis)

    def wheelEvent(self, ev):
        pg.PlotWidget.wheelEvent(self, ev)
        ev.accept()

    def mouseMovedPosition(self, evt):
        leftvb = self.leftAxis.vb
        rightvb = self.rightAxis
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.sceneBoundingRect().contains(pos):
            mousePointLeft = leftvb.mapSceneToView(pos)
            mousePointRight = rightvb.mapSceneToView(pos)
            self.mouseLeftX = round(mousePointLeft.x())
            self.mouseLeftY = float(mousePointLeft.y())
            self.mouseRightY = float(mousePointRight.y())
            leftXString = qtc.QDateTime.fromSecsSinceEpoch(round(self.mouseLeftX)).toString("HH:mm:ss")
            self.mousePositionLabelLeft.setText("(<span style='color: white'>%s</span>, <span style='color: OrangeRed'>%.3f</span>, "
                                                "<span style='color: MediumTurquoise'>%.3f</span>)" %
                                                (leftXString, self.mouseLeftY, self.mouseRightY))
            # self.mousePositionLabelRight.setText("(<span style='color: white'>%s</span>, <span style='color: MediumTurquoise'>%.3f</span>)" %
            #                                      (leftXString, self.mouseRightY))

    def mouseReleaseEvent(self, ev):
        pg.GraphicsView.mouseReleaseEvent(self, ev)
        self.update()

    def mouseMoveEvent(self, ev):
        pg.GraphicsView.mouseMoveEvent(self, ev)
        self.update()

    def mousePressed(self, ev, axis):
        if ev.button() == qtc.Qt.RightButton:
            self.addRegionLineMenuItem(ev)
            self.raiseContextMenu(ev, axis)
        else:
            self.disableAutoRange()
            self.graphScroll = False

        self.update()

    def raiseRightMenu(self, ev):
        ev.accept()
        self.mousePressed(ev, self.rightAxis)

    def raiseLeftMenu(self, ev):
        ev.accept()
        self.mousePressed(ev, self.leftAxis)

    # todo: possibly add mouse scroll handler to stop zooming in/out too much in a way that breaks the graph

    def raiseContextMenu(self, ev, axis):
        pos = ev.screenPos()
        self.menu = self.getContextMenus(ev)
        [[x1,x2],[y1, y2]] = self.viewRange()
        self.yGraphController.changeRangeText(y1, y2)
        self.xGraphController.updateCurrentTime()
        self.menu.axis = axis
        self.menu.popup(qtc.QPoint(int(pos.x()), int(pos.y())))
        return True

    def getContextMenus(self, ev):  # runs only once
        if self.menu is None:
            self.menu = qtw.QMenu()
            self.menu.aboutToHide.connect(self.menuAboutToHide)

            self.menu.addSeparator().setText("Both Axis")
            self.seeAllBoth = qtw.QAction("See All")
            self.seeAllBoth.triggered.connect(lambda x: self.setSeeAll(ViewBox.XYAxes))
            self.menu.addAction(self.seeAllBoth)

            self.menu.addSeparator().setText("Axis")

            #X
            #replace over menu
            # self.menu.xAction = qtw.QAction("X Axis Options")
            # self.menu.xAction.triggered.connect(lambda x: self.showMenu(self.xGraphController, self.menu.pos()))
            # self.menu.addAction(self.menu.xAction)

            #Submenu
            self.menu.groupX = qtw.QMenu("X Axis Options")
            self.menu.actionX = qtw.QWidgetAction(self.menu.groupX)
            self.menu.actionX.setDefaultWidget(self.xGraphController)
            self.menu.groupX.addAction(self.menu.actionX)
            self.menu.addMenu(self.menu.groupX)


            # Y
            self.menu.groupY = qtw.QMenu("Y Axis Options")
            self.menu.actionY = qtw.QWidgetAction(self.menu.groupY)

            self.menu.actionY.setDefaultWidget(self.yGraphController)
            self.menu.groupY.addAction(self.menu.actionY)
            self.menu.addMenu(self.menu.groupY)

            self.menu.addSeparator().setText("Markers")

            #infinitelineItem
            self.menu.infLineAction = qtw.QAction("Add line")
            self.menu.infLineAction.triggered.connect(self.toggleInfiniteLine)
            self.menu.addAction(self.menu.infLineAction)

            #linear region item
            self.menu.linRegAction = qtw.QAction("Add region")
            self.menu.linRegAction.triggered.connect(self.toggleLinearRegion)
            self.menu.addAction(self.menu.linRegAction)

            self.menu.noteAction = qtw.QAction("Add Note")
            self.menu.createNote = self.region
            self.menu.noteAction.triggered.connect(self.addNote)

            self.menu.avgMenu = None
            self.menu.avgAction = None
            self.getAveragesMenu()

        return self.menu

    def showMenu(self, widget, pos):
        widget.show()
        widget.move(int(pos))

    def getAveragesMenu(self):
        if not self.menu.avgMenu:
            self.menu.avgMenuWidget = GraphAveragesController()
            self.menu.avgWidgetAction = qtw.QWidgetAction(self.menu)
            self.menu.avgWidgetAction.setDefaultWidget(self.menu.avgMenuWidget)
            self.menu.avgActionMenu = qtw.QMenu("Plot Average")
            self.menu.avgActionMenu.addAction(self.menu.avgWidgetAction)
            self.menu.addMenu(self.menu.avgActionMenu)
            self.menu.avgMenuWidget.sigAddAverage.connect(self.addAverageCurve)
            self.menu.avgMenuWidget.sigRemoveAverage.connect(self.removeAverage)
            self.menu.avgMenuWidget.sigRemoveAllOnAxis.connect(self.removeAllAverages)
        return self.menu.avgMenu

    def menuAboutToHide(self):
        try:
            self.menu.removeAction(self.menu.noteAction)
            if self.region.visible is False and self.infLine.visible is False:
                self.menu.removeAction(self.menu.removeMarkersAction)
        except Exception:
            pass

    def setGraphRange(self, min, max, axis):
        if self.menu:
            self.menu.close()
        if axis == ViewBox.XAxis:
            self.graphScroll = False
            self.menu.axis.setXRange(int(min), int(max))
        elif axis == ViewBox.YAxis:
            self.menu.axis.setYRange(int(min), int(max))

    def setGraphWidth(self, width):
        if self.menu:
            self.menu.close()
        self.graphScroll = True
        self.graphWidth = width

    def setSeeAll(self, axis):
        if self.menu:
            self.menu.close()
        if axis == ViewBox.XAxis:
            self.setAutoPan(False, False)
            self.graphScroll = False
            self.menu.axis.enableAutoRange(axis)
        elif axis == ViewBox.YAxis:
            if self.graphScroll:
                self.leftAxis.vb.setAutoPan(True, False)
                self.rightAxis.setAutoPan(True, False)
            self.menu.axis.enableAutoRange(axis)
        else:  #Viewbox.XYAxis
            self.leftAxis.vb.setAutoPan(False, False)
            self.rightAxis.setAutoPan(False, False)
            self.graphScroll = False
            self.leftAxis.enableAutoRange(axis)
            self.rightAxis.enableAutoRange(axis)

    def toggleInfiniteLine(self, action):
        if self.infLine.visible:
            self.removeItem(self.infLine)
            self.menu.infLineAction.setText("Add Infinite Line")
            self.infLine.visible = False
        else:
            self.menu.infLineAction.setText("Hide Infinite Line")
            self.infLine.setValue(self.mouseLeftX)
            self.addItem(self.infLine)
            self.infLine.visible = True

    def toggleLinearRegion(self, action):
        if self.region.visible:
            #remove
            self.removeItem(self.region)
            self.region.visible = False
            self.menu.linRegAction.setText("Add Region")
        else:
            #add
            [[x1,x2],[y1,y2]] = self.viewRange()
            diff = x2-x1
            self.menu.linRegAction.setText("Hide Region")
            line1 = self.region.lines[0]
            line2 = self.region.lines[1]
            line1.setValue(int(self.mouseLeftX+diff/20))
            line2.setValue(int(self.mouseLeftX-diff/20))
            self.addItem(self.region)
            self.region.visible = True
            self.update()

    def addRegionLineMenuItem(self, ev):
        if self.infLine.mouseHovering:
            self.menu.createNote = self.infLine
            self.menu.addAction(self.menu.noteAction)

        elif self.region.mouseHovering:
            self.menu.createNote = self.region
            self.menu.addAction(self.menu.noteAction)

    def calculateAverage(self, curves, x1, x2):
        allY = []
        numY = 0
        avgY = 0
        for curve in curves:
            x, y = curve.getDataInRange(x1, x2)
            y = y.tolist()
            allY += y
            numY += len(y)
        for y in allY:
            avgY += y
        if numY == 0:
            return None
        return float(avgY / numY)

    def addAverageCurve(self, axisStr):
        if self.region.visible:
            x1, x2 = self.region.getRegion()
        else:  # uses viewing Range
            [[x1, x2], [y1, y2]] = self.viewRange()
        x1 = round(x1)
        x2 = round(x2)
        if x2 == x1:
            x2 += 1
        curves = self.parent.getVisibleCurves()
        curves = list(filter(lambda x: self.getAxis(x.axis) == self.getAxis(axisStr), curves))
        if len(curves) == 0:
            return None

        avgY = self.calculateAverage(curves, x1, x2)
        if avgY is not None:
            averagePlot = pg.PlotCurveItem([x1, x2], [avgY, avgY])
            self.getAxis(axisStr).addItem(averagePlot)
            averagePlot.label = pg.TextItem(format(avgY, ".3f"), color=(255, 255, 255))
            averagePlot.label.setParentItem(averagePlot)
            averagePlot.label.setPos(x1, avgY)
            if self.getAxis(axisStr) == self.leftAxis:
                self.menu.avgMenuWidget.addAverage("left", avgY)
                self.averagesLeft.append(averagePlot)
            if self.getAxis(axisStr) == self.rightAxis:
                self.averagesRight.append(averagePlot)
                self.menu.avgMenuWidget.addAverage("right", avgY)

    def removeAllAverages(self, axis):
        axis = self.getAxis(axis)
        previousVisibleCurves = self.parent.getVisibleCurves()
        averagesList = self.averagesLeft
        if axis == self.rightAxis:
            averagesList = self.averagesRight

        for average in averagesList:
            axis.removeItem(average)
            average.deleteLater()

        averagesList.clear()

        showncurves = self.parent.getShownCurves()
        for curv in showncurves:
            if curv not in previousVisibleCurves:
                curv.getMainWidget().hide()

    def removeAverage(self, averageIndex, axisStr):
        axis = self.getAxis(axisStr)
        avgList = self.averagesRight
        if axis == self.leftAxis:
            avgList = self.averagesLeft
        avgLen = len(avgList)
        if avgLen > 0:
            curves = self.parent.getVisibleCurves()
            axis.removeItem(avgList[averageIndex])
            avgList[averageIndex].deleteLater()
            avgList.pop(averageIndex)
            showncurves = self.parent.getShownCurves()
            for curv in showncurves:
                if curv not in curves:
                    curv.getMainWidget().hide()

    def addNote(self):
        item = self.menu.createNote
        mb = qtw.QInputDialog(self)
        mb.setWindowTitle("Add Note")
        leftEpoch, rightEpoch, epochPosition = None, None, None
        if item == self.region:
            leftEpoch, rightEpoch = self.region.getRegion()
            mb.setLabelText("Add a note for the region "
                            +qtc.QDateTime.fromSecsSinceEpoch(leftEpoch).toString("HH:mm:ss")+" to "
                            +qtc.QDateTime.fromSecsSinceEpoch(rightEpoch).toString("HH:mm:ss"))
        if item == self.infLine:
            epochPosition = self.infLine.value()
            mb.setLabelText("Add a note for the time "+qtc.QDateTime.fromSecsSinceEpoch(epochPosition).toString("HH:mm:ss"))

        mb.exec()
        note = mb.textValue()
        if len(note) > 0:
            visibleCurves = self.parent.getVisibleCurves()
            visibleCurvesStr=""
            for index, curv in enumerate(visibleCurves):
                if item == self.infLine:
                    latest = curv.getLatest()[1]
                    try:
                        latest = format(float(latest), '.3f')
                    except Exception:
                        latest = "None"
                    visibleCurvesStr += "<br>" + curv.label + " | Value: " + latest
                if item == self.region:
                    x1, x2 = self.region.getRegion()
                    x1 = round(x1)
                    x2 = round(x2)
                    avgY = self.calculateAverage([curv], x1, x2)
                    if avgY is not None:
                        avgYStr = format(avgY, ".3f")
                    else:
                        avgYStr = "None"
                    visibleCurvesStr += "<br>" + curv.label + " | Average: " + avgYStr
            if item == self.region:
                self.createNote.emit(
                    {
                        "Start Time": tu.dtToStr(tu.EpochtoDT(leftEpoch), tu.FormatKeys.ISO8601),
                        "End Time": tu.dtToStr(tu.EpochtoDT(rightEpoch), tu.FormatKeys.ISO8601),
                        "Curves": visibleCurvesStr,
                        "msg": note,
                        "Graph": self.name
                     })
            if item == self.infLine:
                # TODO: Save the note here with whatever data you want (epochPosition, note, visibleCurves, data in those curves)
                self.createNote.emit(
                    {
                        "Note Time": tu.dtToStr(tu.EpochtoDT(epochPosition), tu.FormatKeys.ISO8601),
                        "Curves": visibleCurvesStr,
                        "msg": note,
                        "Graph": self.name
                     })

    def getAxis(self, axis):
        if axis == "left" or axis == "Left Axis":
            return self.leftAxis
        if axis == "right" or axis == "Right Axis":
            return self.rightAxis

class TimeAxisItem(pg.AxisItem):
    """Enhanced PyQtGraph AxisItem to place HH:MM:SS ticks on axis"""
    """AxisItem(orientation, pen=None, linkView=None, parent=None, maxTickLength=-5, showValues=True)"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        return [
            tu.EpochtoDT(value, THIS_TIMEZONE).strftime('%H:%M:%S')
            for value in values
        ]

class GraphController(qtw.QWidget):
    graphRangeSignal = qtc.pyqtSignal(int, int)
    graphWidthSignal = qtc.pyqtSignal(int)
    graphSeeAllSignal = qtc.pyqtSignal(bool)
    hideMenuSignal = qtc.pyqtSignal()

    def __init__(self, axis):
        qtw.QWidget.__init__(self)
        self.axis = axis
        self.layout = qtw.QGridLayout()
        self.setLayout(self.layout)

        if axis == ViewBox.XAxis:
            self.seeAll = self.getSeeAllWidget()
            self.groupStaticDateTimeRange = self.getStaticDateTimeWidget()
            self.groupScrollRange = self.getScrollGroupWidget()
            self.layout.addWidget(self.seeAll)
            self.layout.addWidget(self.groupStaticDateTimeRange)
            self.layout.addWidget(self.groupScrollRange)

        if axis == ViewBox.YAxis:
            self.seeAll = self.getSeeAllWidget()
            self.groupStaticValueRange = self.getStaticValueWidget()
            self.layout.addWidget(self.seeAll)
            self.layout.addWidget(self.groupStaticValueRange)

        self.setWindowFlags(qtc.Qt.Popup)

    def emitRangeInt(self, start, end):
        self.graphRangeSignal.emit(start, end)
        self.hideMenuSignal.emit()

    def emitRangeDateTime(self, start, end):
        # remove time in seconds from time range
        start = start.toSecsSinceEpoch()-start.time().second()
        end = end.toSecsSinceEpoch()-end.time().second()
        self.graphRangeSignal.emit(start, end)
        self.hideMenuSignal.emit()

    def emitWidth(self, width, unit):
        if width:
            try:
                width = float(width)
                width = Conversion.convert(width, unit, 's')
                self.graphWidthSignal.emit(int(width))
                self.hideMenuSignal.emit()
            except Exception:  # probably can't happen due to textfield float validator
                errorbox = qtw.QMessageBox()
                errorbox.setText("Given scrolling range is not valid.")
                errorbox.exec_()

    def seeAllClicked(self):
        self.graphSeeAllSignal.emit(True)
        self.hideMenuSignal.emit()

    def getSeeAllWidget(self):
        newSeeALL = qtw.QPushButton("See All")
        newSeeALL.clicked.connect(self.seeAllClicked)
        return newSeeALL

    def getStaticDateTimeWidget(self):
        groupStaticRange = qtw.QGroupBox("Static Time Range")
        layoutStaticRange = qtw.QGridLayout()
        groupStaticRange.setLayout(layoutStaticRange)

        starttime = qtw.QDateTimeEdit(qtc.QDateTime.currentDateTime())
        groupStaticRange.endtime = qtw.QDateTimeEdit(qtc.QDateTime.currentDateTime())
        startlabel = qtw.QLabel("Start")
        endlabel = qtw.QLabel("End")
        setTimesButton = qtw.QPushButton("Set")
        setTimesButton.clicked.connect(lambda x: self.emitRangeDateTime(starttime.dateTime(), groupStaticRange.endtime.dateTime()))
        layoutStaticRange.addWidget(startlabel, 1, 0)
        layoutStaticRange.addWidget(starttime, 2, 0)
        layoutStaticRange.addWidget(endlabel, 3, 0)
        layoutStaticRange.addWidget(groupStaticRange.endtime, 4, 0)
        layoutStaticRange.addWidget(setTimesButton, 5, 0)

        return groupStaticRange

    def updateCurrentTime(self):
        self.groupStaticDateTimeRange.endtime.setDateTime(qtc.QDateTime.currentDateTime())

    def getScrollGroupWidget(self):
        groupScrollRange = qtw.QGroupBox("Scrolling Time Range")
        layoutScrollRange = qtw.QGridLayout()
        groupScrollRange.setLayout(layoutScrollRange)

        rangetime = qtw.QLineEdit()
        rangetime.setValidator(QtGui.QDoubleValidator())
        rangetime.setText(str(300))

        rangetimeunit = qtw.QComboBox()
        rangetimeunit.addItem("s")
        rangetimeunit.addItem("min")
        rangetimeunit.addItem("hr")
        rangetimeunit.addItem("days")
        setRangeButton = qtw.QPushButton("Set")
        setRangeButton.clicked.connect(lambda: self.emitWidth(rangetime.text(), rangetimeunit.currentText()))
        layoutScrollRange.addWidget(rangetime, 0, 0)
        layoutScrollRange.addWidget(rangetimeunit, 0, 1)
        layoutScrollRange.addWidget(setRangeButton, 1, 0)
        rangetime.returnPressed.connect(lambda: setRangeButton.click())
        return groupScrollRange


    def getStaticValueWidget(self):
        groupStaticValueRange = qtw.QGroupBox("Static Time Range")
        layoutStaticRange = qtw.QGridLayout()
        groupStaticValueRange.setLayout(layoutStaticRange)

        groupStaticValueRange.maxVal = qtw.QLineEdit()
        groupStaticValueRange.maxVal.setValidator(QtGui.QDoubleValidator())
        maxLabel = qtw.QLabel("Max")
        groupStaticValueRange.minVal = qtw.QLineEdit()
        groupStaticValueRange.minVal.setValidator(QtGui.QDoubleValidator())
        minLabel = qtw.QLabel("Min")
        setTimesButton = qtw.QPushButton("Set")
        setTimesButton.clicked.connect(lambda x: self.emitRange(float(groupStaticValueRange.minVal.text()), float(groupStaticValueRange.maxVal.text())))
        groupStaticValueRange.maxVal.returnPressed.connect(lambda: groupStaticValueRange.minVal.setFocus())
        groupStaticValueRange.minVal.returnPressed.connect(lambda: setTimesButton.click())

        layoutStaticRange.addWidget(maxLabel, 1, 0)
        layoutStaticRange.addWidget(groupStaticValueRange.maxVal, 2, 0)
        layoutStaticRange.addWidget(minLabel, 3, 0)
        layoutStaticRange.addWidget(groupStaticValueRange.minVal, 4, 0)
        layoutStaticRange.addWidget(setTimesButton, 5, 0)

        return groupStaticValueRange

    def changeRangeText(self, min, max):
        self.groupStaticValueRange.minVal.setText(str(format(min, '.2f')))
        self.groupStaticValueRange.maxVal.setText(str(format(max, '.2f')))

class GraphAveragesController(qtw.QWidget):
    sigAddAverage = qtc.pyqtSignal(str)
    sigRemoveAverage = qtc.pyqtSignal(int, str)
    sigRemoveAllOnAxis = qtc.pyqtSignal(str)

    def __init__(self):
        qtw.QWidget.__init__(self)
        self.layout = qtw.QGridLayout()
        self.setLayout(self.layout)
        self.addID=0

        self.avgSelectL = qtw.QComboBox()
        self.avgSelectL.currentTextChanged.connect(self.setAverage)
        self.avgSelectR = qtw.QComboBox()
        self.avgSelectR.currentTextChanged.connect(self.setAverage)

        self.addAverageL = qtw.QPushButton("Add")
        self.addAverageL.clicked.connect(lambda x: self.sigAddAverage.emit("left"))
        self.removeAverageL = qtw.QPushButton("Remove")
        self.removeAverageL.clicked.connect(lambda x: self.removeAverage("left"))
        self.addAverageR = qtw.QPushButton("Add")
        self.addAverageR.clicked.connect(lambda x: self.sigAddAverage.emit("right"))
        self.removeAverageR = qtw.QPushButton("Remove")
        self.removeAverageR.clicked.connect(lambda x: self.removeAverage("right"))

        self.removeAllL = qtw.QPushButton("Remove All")
        self.removeAllL.clicked.connect(lambda x: self.removeAllAverages("left"))
        self.removeAllR = qtw.QPushButton("Remove All")
        self.removeAllR.clicked.connect(lambda x: self.removeAllAverages("right"))
        self.removeAll = qtw.QPushButton("Remove All")
        self.removeAll.clicked.connect(lambda x: self.removeAllAverages("both"))

        self.layout.addWidget(qtw.QLabel("Left Axis"), 0, 0)
        self.layout.addWidget(qtw.QLabel("Right Axis"), 0, 1)
        self.layout.addWidget(self.addAverageL, 1, 0)
        self.layout.addWidget(self.addAverageR, 1, 1)
        self.layout.addWidget(self.avgSelectL, 2, 0)
        self.layout.addWidget(self.avgSelectR, 2, 1)
        self.layout.addWidget(self.removeAverageL, 3, 0)
        self.layout.addWidget(self.removeAverageR, 3, 1)
        self.layout.addWidget(self.removeAllL, 4, 0)
        self.layout.addWidget(self.removeAllR, 4, 1)
        self.layout.addWidget(self.removeAll, 5, 0, 1, 2)

    def setAverage(self, average):
        pass

    def removeAverage(self, axisStr):
        if axisStr == "left":
            self.sigRemoveAverage.emit(self.avgSelectL.currentIndex(), "left")
            self.avgSelectL.removeItem(self.avgSelectL.currentIndex())
        else:
            self.sigRemoveAverage.emit(self.avgSelectR.currentIndex(), "right")
            self.avgSelectR.removeItem(self.avgSelectR.currentIndex())

    def removeAllAverages(self, axis):
        if axis == "left":
            self.sigRemoveAllOnAxis.emit(axis)
            self.avgSelectL.clear()
        elif axis == "right":
            self.sigRemoveAllOnAxis.emit(axis)
            self.avgSelectR.clear()
        else:
            self.sigRemoveAllOnAxis.emit("left")
            self.sigRemoveAllOnAxis.emit("right")
            self.avgSelectR.clear()
            self.avgSelectL.clear()

    def addAverage(self, axisStr, avgY):
        self.addID+=1
        if axisStr == "left":
            self.avgSelectL.addItem(str(self.addID) + ": " + format(avgY, ".3f"))
        else:
            self.avgSelectR.addItem(str(self.addID) + ": " + format(avgY, ".3f"))

if __name__ == '__main__':
    import sys
    app = qtw.QApplication(sys.argv)
    menu = GraphAveragesController()
    menu.show()
    sys.exit(app.exec_())