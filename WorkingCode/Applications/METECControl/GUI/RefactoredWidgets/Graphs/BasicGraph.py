import enum
import logging
from threading import RLock

import PyQt5.QtGui as qtg
import PyQt5.QtWidgets as qtw
import numpy as np
import pyqtgraph as pg
from Applications.METECControl.GUI.RefactoredWidgets.Graphs import CustomPlotClasses as cpc
from Applications.METECControl.GUI.RefactoredWidgets.Graphs.GraphLegendWidget import CurveCheckbox
from Applications.METECControl.GUI.RefactoredWidgets.Graphs.GraphLegendWidget import GraphLegendWidget
from Applications.METECControl.GUI.RefactoredWidgets.Graphs.GraphLegendWidget import OutputGroupings
from Framework.BaseClasses.Events import EventTypes, EventPayload
from Framework.BaseClasses.Package import Package
from Framework.BaseClasses.QtMixin import QtMixin, DataWidget
from Utils import Conversion
from Utils import TimeUtils as tu

THIS_TIMEZONE = "US/Mountain"

class Axis(enum.Enum):
    left = 0
    right = 1

class BasicGraph(qtw.QWidget, QtMixin):
    def __init__(self, GUIInterface,
                 name=None, parent=None, label=None, controllerName=None,
                 *args, **kwargs):
        QtMixin.__init__(self, GUIInterface=GUIInterface, name=name, parent=parent, *args, **kwargs)
        qtw.QWidget.__init__(self, parent)

        # PlotWidget is a single PlotItem wrapped by GraphicsView widget. The fields Parent and Background are passed
        # to GraphicsView widget, and everything else is passed to PlotItem. Use getPlotItem to access the wrapped PlotItem.
        self.ctrlName = controllerName
        self.title = label if label else name
        self.layout = qtw.QHBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)

        self.timeAxis = cpc.TimeAxisItem(orientation='bottom')
        self.mainWidget = cpc.CustomPlot(self, title=self.title, axisItems={"bottom":self.timeAxis})
        self.mainWidget.setMinimumWidth(500)
        self.mainWidget.setLabels(title=self.title)
        self.mainWidget.createNote.connect(self.createNote)

        self.legendContainer = qtw.QWidget(self)
        self.legendLayout = qtw.QGridLayout(self.legendContainer)
        self.legendLayout.setSpacing(5)
        self.legendLayout.setContentsMargins(0,0,0,0)
        self.legendLocation = 0
        self.legendSpacer = qtw.QSpacerItem(1, 1, qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Expanding)
        self.legendLayout.addItem(self.legendSpacer, 0, 0, 1, 2)

        self.layout.addWidget(self.legendContainer)

        self.outputGroupingOrganizer = OutputGroupings(GUIInterface, name + "_outputGroupingOrganizer", self, None)
        self.outputGroupingOrganizer.newOutputGrouping.connect(self.changeOutputGrouping)
        self.layout.addWidget(self.outputGroupingOrganizer)
        self.outputGrouping = None

        self.layout.addWidget(self.mainWidget)

        self.widgets = {}
        self.curves = {}

        # # Uncomment this for a linear region.
        # self.linRegItem = pg.LinearRegionItem()
        # self.mainWidget.addItem(self.linRegItem)
        self.bottomAxis = self.mainWidget.getAxis('bottom')

    def update(self):
        for widgetName, widgets in self.widgets.items():
            cItem = widgets['CurveItem']
            lItem = widgets['LegendItem']
            lItem.update()
            cItem.update()
        self.mainWidget.update()

    def graphContextMenu(self, event):
        self.rightClickMenu.show()

    def updateUnit(self, unitAbbr, name):
        group = self.widgets[name]['CurveItem'].outputGrouping
        inputUnitType = Conversion.getUnitType(self.widgets[name]['LegendItem'].outputBox.getInputUnit())
        for singleStream in self.widgets.values():
            lItem = singleStream['LegendItem']
            cItem = singleStream['CurveItem']
            # if cItem.outputGrouping == group and group is not None and Conversion.getUnitType(lItem.outputBox.getInputUnit()) == inputUnitType:
            try:
                lItem.changeUnit(unitAbbr)
                cItem.changeUnit(unitAbbr)
            except Exception as e:
                logging.error(e)
        # TODO: right now causes an error if menu has not been set.
        # self.mainWidget.yGraphController.seeAllClicked()

    def changeOutputGrouping(self, group):
        """
        called when outputGroupings organizer emits newOutputGroup signal
        :param group: new group
        :return: None
        """
        self.outputGrouping = group

    def getMainWidget(self):
        return self

    def addCurveItem(self, name=None, label=None, corrSource=None, corrField=None, corrUnits=None, rawSource=None, rawField=None, rawUnits=None, outputGrouping=None, sensorProperties=None, pen=None):
        thisSensor = sensorProperties.get(name, {})
        if not corrUnits:
            corrUnits = thisSensor.get('output_units')
        if not rawUnits:
            rawUnits = thisSensor.get('raw_units')
        label = label if label else name

        curve = CurveItem(self.GUIInterface, name=name, parent=self, corrSource=corrSource, corrField=corrField, corrUnits=corrUnits,
                          rawSource=rawSource, rawField=rawField, rawUnits=rawUnits, outputGrouping=outputGrouping, pen=pen)

        checkbox = CurveCheckbox(label, self.outputGroupingOrganizer, outputGrouping, curve)
        self.outputGroupingOrganizer.addCheckbox(checkbox)

        legendWidget = GraphLegendWidget(self.GUIInterface, name=name + "_legend", parent=self, unitDict=curve.unitDict, label=label, color=curve.color,
                                         corrSource = corrSource, corrField=corrField, corrUnits=corrUnits,
                                         rawSource=rawSource, rawField=rawField, rawUnits=rawUnits, sensorproperties=thisSensor)

        legendRow = int(self.legendLocation/2) # divide by two rounded down.
        legendCol = self.legendLocation % 2 # mod 2.
        self.legendLocation += 1
        self.legendLayout.removeItem(self.legendSpacer)
        # Add the new legend item to the top left, then top right, going throuh each row sequentially.
        self.legendLayout.addWidget(legendWidget, legendRow, legendCol)
        # add a legend spacer to compactify
        self.legendLayout.addItem(self.legendSpacer, legendRow+1, 0, 1, 2)

        self.widgets[name] = {'CurveItem': curve,
                              'LegendItem': legendWidget,
                              'unitChanged': lambda x: self.updateUnit(x, name),
                              'axisChange': lambda x: self.changeAxis(name, x),
                              'CheckBox': checkbox,
                              'newState': lambda x: self.newState(name, x)
                              }
        if checkbox.getChecked():
            self.legendToggle(name)
            self.addCurve(curve, Axis.right)

        checkbox.newStateSignal.connect(self.widgets[name]['newState'])
        legendWidget.axisChanged.connect(self.widgets[name]['axisChange'])
        legendWidget.unitChanged.connect(self.widgets[name]['unitChanged'])

    def addCurve(self, curve, axis=Axis.right):
        self.curves[curve.name] = curve
        curve.axis = axis
        if axis == Axis.right:
            self.mainWidget.rightAxis.addItem(curve.getMainWidget())
        elif axis == Axis.left:
            self.mainWidget.leftAxis.addItem(curve.getMainWidget())

    def removeCurve(self, curve):
        self.curves[curve.name].getMainWidget().clear()
        axis = curve.axis
        if axis == Axis.right:
            self.mainWidget.rightAxis.removeItem(curve.getMainWidget())
        elif axis == Axis.left:
            self.mainWidget.leftAxis.removeItem(curve.getMainWidget())

    def toggleCurve(self, curve):
        if curve.visible:
            curve.visible = False
            self.removeCurve(curve)
        else:
            curve.visible = True
            self.addCurve(curve, curve.axis)

    def newState(self, name, state):
        curveItem = self.widgets[name]['CurveItem']
        if not state == curveItem.visible:
            self.legendToggle(name)
        if not state:
            self.removeCurve(curveItem)
        else:
            self.addCurve(curveItem)

    def legendToggle(self, name):
        curveItem = self.widgets[name]['CurveItem']
        legendItem = self.widgets[name]['LegendItem']
        if legendItem.visible != curveItem.visible:  # in case they become un-synced at some point, probably unnecessary
            legendItem.toggle()

    def curveColorUpdate(self, legendWidget, qColor):
        corWidget = list(filter(lambda x: x["LegendItem"] == legendWidget, self.widgets.values()))
        corWidget=corWidget[0]
        curveWidget = corWidget["CurveItem"]
        curveWidget.setColor(qColor)

    def getVisibleCurves(self):
        items = list(filter(lambda x: x["CurveItem"].visible, self.widgets.values()))
        for i in range(len(items)):
            items[i] = items[i]["CurveItem"]
        return items

    def getShownCurves(self):
        items = list(filter(lambda x: x["CurveItem"].getMainWidget().isVisible(), self.widgets.values()))
        for i in range(len(items)):
            items[i] = items[i]["CurveItem"]
        return items

    def getAxisFromStr(self, axis):
        if axis == 'Right Axis':
            return Axis.right
        elif axis == "Left Axis":
            return Axis.left
        else:
            return Axis.right

    def changeAxis(self, name, axisText):
        # previousVisibleCurves = self.getShownCurves()
        axis = self.getAxisFromStr(axisText)
        cItem = self.widgets[name]['CurveItem']
        cItem.axis = axis
        dataItem = cItem.getMainWidget()
        if axis == Axis.right:
            self.mainWidget.leftAxis.removeItem(dataItem)
            self.mainWidget.rightAxis.addItem(dataItem)
        elif axis == Axis.left:
            self.mainWidget.rightAxis.removeItem(dataItem)
            self.mainWidget.leftAxis.addItem(dataItem)
        # showncurves = self.getShownCurves()
        # for curv in showncurves:
        #     if curv not in previousVisibleCurves:
        #         curv.getMainWidget().hide()

    def createNote(self, data):
        eventPld = EventPayload(source=self.GUIInterface.name, eventType=EventTypes.Annotation, timestamp=tu.nowEpoch(), **data)
        eventPkg = Package(self.GUIInterface.name, payload=eventPld)
        self.GUIInterface.emitEvent(eventPkg)

class CurveItem(DataWidget):
    def __init__(self, GUIInterface,
                 name=None, parent=None, corrSource=None, corrField=None, corrUnits = None,
                 rawSource=None, rawField=None, rawUnits=None, pen=None,
                 outputGrouping=None,
                 *args, **kwargs):
        QtMixin.__init__(self, GUIInterface, name, parent, *args, **kwargs)
        self.mainItem = pg.PlotCurveItem(*args, **kwargs)
        self.axis = Axis.right

        self.corrSource = corrSource
        self.corrField = corrField
        self.rawSource = rawSource
        self.rawField = rawField

        self.corrUnits = self.outputUnits = corrUnits
        self.rawUnits = rawUnits

        self.unitType, self.unitDict = Conversion.getDict(self.outputUnits)

        self.lock = RLock()
        if isinstance(pen, qtg.QPen):
            self.pen = pen
        else:
            penInfo = pen if pen else {}
            self.pen = pg.mkPen(**penInfo)
        self.color = self.pen.color()
        self.mainItem.setPen(self.pen)
        self.visible = False

        self.outputGrouping = outputGrouping

    def setRawValue(self, rawFieldname=None, rawValue=None):
        raise NotImplementedError

    def setCorrValue(self, corrFieldname=None, corrValue=None):
        raise NotImplementedError

    def update(self):
        with self.lock:
            x, y = self.GUIInterface.getFieldValues(sourceName=self.corrSource, fieldName=self.corrField)
            if y.size > 0:
                outputY = np.vectorize(Conversion.convert)(y, self.corrUnits, self.outputUnits)
                self.mainItem.updateData(x=x, y=outputY)

    def changeUnit(self, newUnits):
        self.outputUnits = newUnits

    def setColor(self, qColor):
        self.color = qColor
        self.pen.setColor(self.color)
        self.mainItem.setPen(self.pen)

    def setAxis(self, axis):
        self.axis = axis

    def getMainWidget(self):
        return self.mainItem
