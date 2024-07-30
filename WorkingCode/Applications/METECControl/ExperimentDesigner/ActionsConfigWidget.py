import math

import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg
import PyQt5.QtWidgets as qtw
import numpy as np
import pandas as pd  # intent: pandas writing and reading excel also needs packages 'xlrs' and 'openpyxl'
import pyqtgraph as pg
from Applications.METECControl.ExperimentDesigner.DesignerConfigs import EmissionCategories, getEmissionCategory, \
    ShorthandHelper
from Applications.METECControl.ExperimentDesigner.EventsTable import EventsTable
from Applications.METECControl.ExperimentDesigner.ExperimentWidgets import EmissionPointSelector
from Applications.METECControl.ExperimentDesigner.PresetActions import StairPreset, IntermittentPreset
from Utils import Conversion
from Utils.ExperimentUtils import epToColor
from Utils.FlowRateCalculator import calculateQg, getValveColumns, orificeToCv

RAW_UNIT = "SCFH"


class ActionsConfigWidget(qtw.QWidget):

    durationsChanged = qtc.pyqtSignal(int, int, int)

    def __init__(self, menubar, savedir='./'):
        qtw.QWidget.__init__(self)
        self.layout = qtw.QGridLayout()
        self.setLayout(self.layout)
        self.initPresetMenu(menubar)
        self.initTableMenu(menubar)
        self.savedir = savedir
        self.dialog = qtw.QFileDialog()
        #graph
        self.graph = pg.PlotWidget(self)
        self.graph.plotItem.setLabel("left", "Flow Rate", "SLPM", "SLPM")
        self.graph.plotItem.setLabel("bottom", "Time", "Seconds", "s")
        self.curves = {}
        self.fmFlows = {}
        # self.timeRect = qtg.QGraphicsRectItem(0,0,0,0)
        self.timeRect = qtw.QGraphicsRectItem(0, 0, 0, 0)
        self.timeRect.setPen(pg.mkPen(255, 50, 50))
        # self.graph.addItem(self.timeRect)
        self.curve_maxFlowRate = self.graph.plot()  # plotdataitem of total flowrate over time
        self.curve_maxFlowRate.hide()
        self.curve_fmFlowRate = self.graph.plot(width=5, style=qtc.Qt.DotLine)
        self.curve_fmFlowRate.hide()
        self.curve_maxFMFlow = pg.InfiniteLine(pos=100, angle=0, label="FM Max")
        self.curve_preCalLine = pg.InfiniteLine(pos=0, angle=90, label="Pre Cal End", labelOpts={"angle":60})
        self.curve_postCalLine = pg.InfiniteLine(pos=1, angle=90, label="Post Cal Start", labelOpts={"angle": 60})
        self.curve_preCalLine.hide()
        self.curve_postCalLine.hide()
        self.graph.addItem(self.curve_maxFMFlow)
        self.graph.addItem(self.curve_preCalLine)
        self.graph.addItem(self.curve_postCalLine)
        self.xData = [0,1]
        #table
        self.table = EventsTable(menubar, rawUnit=RAW_UNIT)
        self.table.dataChanged.connect(self.updateGraphAndTable)
        self.table.clicked.connect(self.tableClicked)
        self.table.colorChanged.connect(self.setEPColor)
        self.table.removedEPs.connect(self.removedEPSlot)
        self.table.changeEP.connect(self.changeEventEP)
        self.table.resizeColumnsToContents()
        self.epColors = {}  # colors of graph pen and table background color keyed to emission point name
        self.selectedEP:str = None  # currently selected EP to bolden it's curve on graph and show on ep selector
        self.lastID = 0  # last id used. incremented by 1 to get next ID.
        self.table.flowLevelChanged.connect(self.recalculateFlowRate)
        # configs from mainwidget laoding
        self.epConfig = None
        self.fmConfig = None
        self.spansConfig = None
        self.pressuresConfig = None
        self.val_atm = 12.5
        self.val_temp = 70
        self.val_sg = 0.554
        self.val_k = 0.75
        # add new line
        self.select_ep = EmissionPointSelector()
        self.select_ep.currentEPChanged.connect(self.epSelectorSlot)
        self.select_ep.currentFiltersChanged.connect(self.setEPFilters)
        self.select_unit = qtw.QComboBox()
        massflowUnits = Conversion.getDict('massflow')[1]
        self.select_unit.addItems(list(massflowUnits.keys()))
        self.select_unit.currentTextChanged.connect(self.slot_unitChanged)
        self.slot_unitChanged(self.select_unit.currentText())
        self.check_applyFiltersTable = qtw.QCheckBox("Apply filters to Table/Graph")
        self.check_applyFiltersTable.stateChanged.connect(lambda x: self.setEPFilters(*self.select_ep.getFilters()))
        self.label_flowLevel = qtw.QLabel(text="Flow Level")
        self.input_flowLevel = qtw.QSpinBox()
        self.input_flowLevel.setRange(0,15)
        self.label_flowTiming = qtw.QLabel(text="Flow Timing (s)")
        self.input_flowTiming = qtw.QSpinBox()
        self.input_flowTiming.setRange(-99999999, 99999999)
        self.label_linkedID = qtw.QLabel(text="Link ID")
        self.input_linkedID = qtw.QSpinBox()
        self.input_linkedID.setRange(0,99999999)
        self.label_linkedTiming = qtw.QLabel(text="Relative Time (s)")
        self.input_linkedTiming = qtw.QSpinBox()
        self.input_linkedTiming.setRange(-99999999,99999999)
        self.input_intent = qtw.QLineEdit()
        self.input_intent.setPlaceholderText("Add an intent")
        self.input_category = qtw.QComboBox()
        self.input_category.addItems(list(map(lambda x: x.value, EmissionCategories)))
        self.button_addAction = qtw.QPushButton(text="Add Time Event")
        self.button_addAction.clicked.connect(self.clicked_addEvent)
        self.button_addActionLink = qtw.QPushButton(text="Add Linked Event")
        self.button_addActionLink.clicked.connect(self.clicked_addLinkedEvent)
        self.error_maxFlowLevel = qtw.QErrorMessage(self)
        self.check_showFMFlow = qtw.QCheckBox(text="Show FM Flow Curve")
        self.check_showFMFlow.stateChanged.connect(self.showHideFMFlowCurve)
        self.check_showTotalFlow = qtw.QCheckBox(text="Show Total Flow Curve")
        self.check_showTotalFlow.stateChanged.connect(self.showHideTotalFlowCurve)

        #layout
        addWidget = qtw.QWidget()
        addLayout = qtw.QGridLayout()
        addWidget.setLayout(addLayout)
        addWidget.setFixedWidth(250)
        self.graph.setMinimumHeight(350)
        self.layout.addWidget(self.graph, 1, 1, 1, 5)
        self.layout.addWidget(addWidget, 2, 1)
        self.layout.addWidget(self.table, 2, 2, 1, 4)
        addLayout.addWidget(qtw.QLabel(text="Unit"), 0, 1, 1, 1, alignment=qtc.Qt.AlignRight)
        addLayout.addWidget(self.select_unit, 0, 2, 1, 1, alignment=qtc.Qt.AlignLeft)
        addLayout.addWidget(self.check_applyFiltersTable, 1, 1, 1, 2)
        addLayout.addWidget(self.check_showFMFlow, 2, 1, 1, 2)
        addLayout.addWidget(self.check_showTotalFlow, 3, 1, 1, 2)
        addLayout.addWidget(self.select_ep, 4, 1, 1, 2)
        addLayout.addWidget(self.label_flowLevel, 5, 1)
        addLayout.addWidget(self.label_flowTiming, 5, 2)
        addLayout.addWidget(self.input_flowLevel, 6, 1)
        addLayout.addWidget(self.input_flowTiming, 6, 2)
        addLayout.addWidget(self.label_linkedID, 7, 1)
        addLayout.addWidget(self.label_linkedTiming, 7, 2)
        addLayout.addWidget(self.input_linkedID, 8, 1)
        addLayout.addWidget(self.input_linkedTiming, 8, 2)
        addLayout.addWidget(self.input_intent, 9, 1, 1, 2)
        addLayout.addWidget(self.input_category, 10, 1, 1, 2)
        addLayout.addWidget(self.button_addAction, 11, 1, 1, 1)
        addLayout.addWidget(self.button_addActionLink, 11, 2, 1, 1)

    def initPresetMenu(self, menubar):
        # preset menu
        presetMenu = menubar.addMenu("Presets")

        presetStairsMenu = presetMenu.addMenu("Stairs")
        stairsWidgetAction = qtw.QWidgetAction(presetStairsMenu)
        self.preset_stair = StairPreset()
        self.preset_stair.finishedAdding.connect(self.updateGraphAndTable)
        self.preset_stair.createAction.connect(self.addPresetActions)
        stairsWidgetAction.setDefaultWidget(self.preset_stair.getSetupWidget())
        presetStairsMenu.addAction(stairsWidgetAction)

        presetIntermittentMenu = presetMenu.addMenu("Intermittent")
        self.preset_Intermittent = IntermittentPreset()
        self.preset_Intermittent.finishedAdding.connect(self.updateGraphAndTable)
        self.preset_Intermittent.createAction.connect(self.addPresetActions)
        intermittentWidgetAction = qtw.QWidgetAction(presetIntermittentMenu)
        intermittentWidgetAction.setDefaultWidget(self.preset_Intermittent.getSetupWidget())
        presetIntermittentMenu.addAction(intermittentWidgetAction)

        presetStopAll = presetMenu.addAction("Stop All")
        presetStopAll.triggered.connect(self.stopAllEmissions)
        self.presets = [self.preset_Intermittent, self.preset_stair]

    def initTableMenu(self, menubar):
        tableMenu = menubar.addMenu("Table")
        action_clear = tableMenu.addAction("Clear Table")
        action_resetIDs = tableMenu.addAction("Reset IDs")
        action_clear.triggered.connect(self.clearTable)
        action_resetIDs.triggered.connect(self.resetIDs)

        action_saveTable = tableMenu.addAction("Save Table")
        action_saveTable.triggered.connect(self.saveTable)
        action_loadTable = tableMenu.addAction("Load Table")
        action_loadTable.triggered.connect(self.loadTable)

    def getActions(self) -> pd.DataFrame:
        return self.table.getDF()

    def getPostCalStartTime(self):
        df = self.table.getDF()
        postCalEvents = self.table.getPostCalEvents()
        if len(df) == 0:
            return 0
        elif len(postCalEvents) > 0:
            return df.loc[self.table.getPostCalEvents()[0], "Timing"]
        else:
            return df['Timing'].max()+1

    def getPreCalEvents(self):
        return self.table.getPreCalEvents()

    def getPostCalEvents(self):
        return self.table.getPostCalEvents()

    ########### Setters #############
    def setEPConfig(self, epConfig):
        self.epConfig = epConfig
        self.select_ep.setEPConfig(epConfig)
        self.table.setEPConfig(epConfig)
        for preset in self.presets:
            preset.setEPConfig(epConfig)

    def setFMConfig(self, fmConfig:pd.DataFrame):
        self.fmConfig = fmConfig
        self.refreshFlowMeters()

    def setOrificeConfig(self, spansConfig):
        self.spansConfig = spansConfig

    def setPressuresConfig(self, pressuresConfig):
        self.pressuresConfig = pressuresConfig

    def setConfigValues(self, atm, temp, sg, k):
        self.val_atm = atm
        self.val_temp = temp
        self.val_sg = sg
        self.val_k = k

    def setCalPeriod(self, pre, post, on, off):
        with self.table.dfLock:
            actions = self.getActions()
            actions = actions.drop(self.table.getPreCalEvents())
            actions = actions.drop(self.table.getPostCalEvents())
            self.table.setDF(actions)
            if pre or post:
                lastActionTime = actions['Timing'].max()
                expCals = self.approveExperimentCals(actions)
                actions = actions.drop(expCals)  # drop ep levels where it's the only flow from that flow meter
                usedFMs = actions['Flow Meter'].unique()
                uniqueEPtoFMtoLevel = actions.loc[actions['Flow Level'] != 0].groupby(["Emission Point", "Flow Meter", "Flow Level"]).size().reset_index().rename(columns={0:"count"})
                calLength = uniqueEPtoFMtoLevel.groupby(["Flow Meter"]).size().max() * (on+off) # max number of ep levels per flow meters out of all flow meters
                for fm in usedFMs:
                    epLevelForFM = uniqueEPtoFMtoLevel.loc[uniqueEPtoFMtoLevel['Flow Meter'] == fm]
                    time = 0
                    for index, epLevel in epLevelForFM.iterrows():
                        ep, level = epLevel['Emission Point'], epLevel['Flow Level']
                        if pre:
                            self.addEPEvent(ep, level, -calLength - 1 + time, fm, "", category=EmissionCategories.PreTest)
                        if post:
                            self.addEPEvent(ep, level, lastActionTime + 1 + time, fm, "", category=EmissionCategories.PostTest)
                        time += on
                        if pre:
                            self.addEPEvent(ep, 0, -calLength - 1 + time, fm, "", category=EmissionCategories.PreTest)
                        if post:
                            self.addEPEvent(ep, 0, lastActionTime + 1 + time, fm, "", category=EmissionCategories.PostTest)
                        time += off
                    # lastTimeEvents =
            self.updateGraphAndTable()

    def approveExperimentCals(self, df):
        approveDialog = qtw.QDialog()
        approveDialog.setLayout(qtw.QGridLayout())
        approveDialog.layout().addWidget(qtw.QLabel('Approve experiment emissions to replace cals in pre test.'))
        checkableList = qtw.QListWidget()
        approveDialog.layout().addWidget(checkableList, 1,0)
        df:pd.DataFrame
        expIndexes = df.loc[df['Flow Rate'] == df['Total FM Flow']].index
        df = df.sort_values("Timing")
        for eid in expIndexes:
            i = df.index.get_loc(eid)
            startTime = df.loc[eid, 'Timing']
            endI = i+1
            if endI < len(df):
                endTime = df.iloc[endI]['Timing']
                length = endTime-startTime
            else:
                length = 1

            item = qtw.QListWidgetItem()
            item.setData(qtc.Qt.EditRole, eid)
            item.setFlags(item.flags() & ~qtc.Qt.ItemIsSelectable)
            cb = qtw.QCheckBox()
            cb.setText(f"EP: {df.loc[eid, 'Emission Point']}, Level: {df.loc[eid, 'Flow Level']}, Time: {df.loc[eid, 'Timing']}, length: {length}")
            checkableList.addItem(item)
            checkableList.setItemWidget(item, cb)
        approveDialog.exec()
        approved = []
        for i in range(checkableList.count()):
            item = checkableList.item(i)
            cb = checkableList.itemWidget(item)
            if cb.isChecked():
                approved.append(item.data(qtc.Qt.EditRole))
        return approved


    def addPresetActions(self, ep, time, level, category, intent):
        if ep is None:
            ep = self.select_ep.getCurrentEP()
        fm = self.getFMfromEP(ep)
        self.addEPEvent(ep, level, time, fm, intent, category=category)

    def stopAllEmissions(self):
        with self.table.dfLock:
            df = self.table.getDF()
            maxTime = df['Timing'].max()
            for ep in df['Emission Point'].unique():
                self.addEPEvent(ep, 0, maxTime + 1, self.getFMfromEP(ep), "Stop All")
        self.updateGraphAndTable()

    ######## other methods

    def recalculateFlowRate(self, eID, ep, newLevel, oldLevel):
        """ qtsignal slot for when flow level is edited directly by the table
        recalculates flow rate and sets value in table. table.setFlowRates emits dataChanged() which updates graph"""
        maxFlowLevel = self.getMaxFlowLevel(ep)
        if maxFlowLevel < newLevel:
            ...  # error
            self.table.editEvent(eID, {"Flow Level": oldLevel})
            self.error_maxFlowLevel.showMessage(f"Cannot set Emission Point {ep} above flow level {maxFlowLevel}.", None)
        else:
            fr = self.calculateFlowRate(ep, newLevel)
            self.table.setFlowRates({eID: fr})

    def getCBfromEP(self, ep):
        shorthand = self.epConfig.loc[self.epConfig['Emission Point'] == ep, 'Shorthand'].iloc[0]
        shHelper = ShorthandHelper(shorthand)
        return shHelper.cb

    def getRowfromEP(self, ep):
        return self.epConfig.loc[self.epConfig['Emission Point'] == ep].iloc[0]['Row']


    def getFMfromEP(self, ep):
        self.fmConfig:pd.DataFrame
        controller = self.getCBfromEP(ep)
        row = self.getRowfromEP(ep)
        matchingController = self.fmConfig.loc[self.fmConfig['Controller'] == controller]
        matchingController.update(matchingController['Row'].fillna(row).astype(int))
        fm = matchingController[matchingController['Row']==row].iloc[0]['Flowmeter ID']
        return fm

    @qtc.pyqtSlot(str)
    def epSelectorSlot(self, ep):
        self.table.clearSelection()
        self.setSelectedEP(ep)

    @qtc.pyqtSlot(int)
    def showHideFMFlowCurve(self, state):
        if state == 2:
            self.curve_fmFlowRate.show()
        else:
            self.curve_fmFlowRate.hide()

    @qtc.pyqtSlot(int)
    def showHideTotalFlowCurve(self, state):
        if state == 2:
            self.curve_maxFlowRate.show()
        else:
            self.curve_maxFlowRate.hide()

    def slot_unitChanged(self, newUnit):
        self.table.setUnit(newUnit)
        self.updateGraphAndTable()
        self.graph.plotItem.setLabel("left", "Flow Rate", newUnit, newUnit)
        self.updateMaxFMFlow()

    def updateMaxFMFlow(self,ep=None):
        try:
            if ep is None:
                ep = self.select_ep.getCurrentEP()
            maxFMFlow = float(self.spansConfig.loc[self.spansConfig['Flow Name'] == self.getFMfromEP(ep), "Orifice"].item())
            curText = self.select_unit.currentText() if self.select_unit.currentText() else 'SLPM'
            maxFMFlow = Conversion.convert(maxFMFlow, 'SLPM', curText)  # slpm is the max fm flow unit in the spansconfig
            maxFMFlow *= self.val_k
            self.curve_maxFMFlow.setPos(maxFMFlow)
        except AttributeError:
            pass

    def tableClicked(self, index:qtc.QModelIndex):
        df = self.table.getDisplayDF()
        index.row()
        rowData = df.iloc[index.row()]
        ep = rowData['Emission Point']
        self.setSelectedEP(ep)
        self.select_ep.setSelectedEP(ep)
        # self.showFMSpan(rowData['Timing'], rowData['Total FM Flow'])

    def setSelectedEP(self, ep:str):
        if type(ep) is str:
            """ set ep that's curve pen will be set to bold
            Set constraints to flow level
            Show max flow for flowmeter tied to this ep """
            self.setBoldEP(ep)
            # show flow meter flow rate
            fm = self.fmFlows.get(self.getFMfromEP(ep))
            self.updateMaxFMFlow(ep)
            if fm is not None:
                self.curve_fmFlowRate.setData(self.xData, fm)
                self.curve_fmFlowRate.setPen(width=5, style=qtc.Qt.DotLine)
                if self.check_showFMFlow.isChecked():
                    self.curve_fmFlowRate.show()
            else:
                self.curve_fmFlowRate.hide()
            self.selectedEP = ep
            for preset in self.presets:
                preset.setSelectedEP(ep)
                self.input_flowLevel.setMaximum(self.getMaxFlowLevel(ep))

    def setBoldEP(self, ep):
        # bolden selected curve
        oldCurve = self.curves.get(self.selectedEP)
        if oldCurve:
            oldCurve.setPen(self.epColors.get(self.selectedEP))  # remove previous bold line
        newCurve = self.curves.get(ep)
        if newCurve:
            newCurve.setPen(pg.mkPen(color=self.epColors.get(ep), width=4))  # set new bold line

    def getMaxFlowLevel(self, ep):
        maxColumn = int(self.epConfig.loc[self.epConfig['Emission Point'] == ep, 'Column'].item())
        if maxColumn == 4:
            return 7
        else:
            return 15

    def setEPFilters(self, pad, controller):
        if self.check_applyFiltersTable.isChecked():
            self.table.setFilters(pad, controller)
        else:
            if self.table.filters != (None, None):
                self.table.setFilters(None, None)
        self.updateGraphAndTable()

    @qtc.pyqtSlot(str, tuple)
    def setEPColor(self, ep, rgbTuple):
        """ slot for table change color"""
        self.epColors[ep] = rgbTuple
        self.updateGraphAndTable()

    def updateGraphAndTable(self):
        self.table.recalculateAllFlowMeterRates()
        self.table.updateTable()
        df = self.table.getDisplayDF()
        durations = self.calculateDurations(df)
        if durations[0] > 0:
            self.curve_preCalLine.show()
        else:
            self.curve_preCalLine.hide()
        if durations[2] > 0:
            self.curve_postCalLine.setValue(durations[1])
            self.curve_postCalLine.show()
        else:
            self.curve_postCalLine.hide()
        self.durationsChanged.emit(*durations)
        if len(df) > 0:
            x, y, epFlows, self.fmFlows = self.analyzeActionsTable(df)
            self.xData = x
            for ep, flow in epFlows.items():
                color = self.getEPColor(ep)
                plot = self.curves.get(ep,self.graph.plot(pen=color))
                plot.setData(x, flow)
                plot.setPen(self.epColors[ep])
                self.curves[ep] = plot
                plot.show()
            epRemoved = [ep for ep in self.curves.keys() if ep not in epFlows.keys()]
            for ep in epRemoved:
                self.curves[ep].hide()
            self.curve_maxFlowRate.setData(x, y)
            if self.selectedEP:
                fmFlow = self.fmFlows.get(self.getFMfromEP(self.selectedEP))
                if fmFlow is not None:
                    self.curve_fmFlowRate.setData(x, fmFlow)
                else:
                    self.curve_fmFlowRate.hide()

    def calculateDurations(self, df):
        preExpDir = abs(df.loc[df['Emission Category'] == EmissionCategories.PreTest.value, "Timing"].min())
        firstPostExp = df.loc[df['Emission Category'] == EmissionCategories.PostTest.value, "Timing"].min()
        if math.isnan(firstPostExp):
            expDir = df['Timing'].max()+1
        else:
            expDir = firstPostExp
        postExpDir = df['Timing'].max()+1-df.loc[df['Emission Category'] == EmissionCategories.PostTest.value, "Timing"].min()
        preExpDir = 0 if math.isnan(preExpDir) else int(preExpDir)
        expDir = 0 if math.isnan(expDir) else int(expDir)
        postExpDir = 0 if math.isnan(postExpDir) else int(postExpDir)
        return preExpDir, expDir, postExpDir

    def analyzeActionsTable(self, df: pd.DataFrame):
        self.table.model().clearBackgrounds(self.table.model().color_ABrowConflict)
        self.table.model().clearBackgrounds(self.table.model().color_epConflict)
        maxTime = df["Timing"].max()
        minTime = min(df['Timing'].min(), 0)
        graphRange = (maxTime-minTime+1)*2
        x = np.zeros(graphRange)
        uniqueEPS = df['Emission Point'].unique()
        uniqueFMS = df['Flow Meter'].unique()
        epFlows = {ep: np.zeros(graphRange) for ep in uniqueEPS}
        fmFlows = {fm: np.zeros(graphRange) for fm in uniqueFMS}
        totalFlows = np.zeros(graphRange)
        graphIndex = 0
        enabledEPs = set()
        for time in range(minTime, maxTime+1):
            events = df.loc[df["Timing"] == time]
            seenEP = []
            for index, row in events.iterrows():
                ep = row['Emission Point']
                if row['Flow Level'] > 0:
                    enabledEPs.add(ep)
                elif ep in enabledEPs:
                    enabledEPs.remove(ep)
                self.checkForInvalidEP_AB(ep, index, enabledEPs)
                # EP conflict background highlighter
                if row['Emission Point'] in seenEP:
                    self.table.model().changeBackgroundColor(row.name, self.table.model().color_epConflict, True)
                else:
                    seenEP.append(row['Emission Point'])
                # calculate flow from flow rate
                fr = row['Flow Rate']
                if fr == "":
                    fr = 0
                epFlows[row['Emission Point']][graphIndex:] = fr
            totalFlowAtTime = sum([flow[graphIndex] for flow in epFlows.values()])
            totalFlows[graphIndex] = totalFlowAtTime
            totalFlows[graphIndex+1] = totalFlowAtTime
            x[graphIndex] = time
            x[graphIndex+1] = time+1
            graphIndex += 2
        for fm in uniqueFMS:
            includedEPs = df.loc[df['Flow Meter'] == fm, "Emission Point"].unique()
            for ep in includedEPs:
                fmFlows[fm] += epFlows[ep]
        return x, totalFlows, epFlows, fmFlows


    def checkForInvalidEP_AB(self, ep, index, enabledEPs):
        invalidEPs = self.getInvalidEPsForAB(ep)
        conflictEPs = set.intersection(set(enabledEPs), set(invalidEPs))
        if len(conflictEPs) > 0:
            self.table.model().changeBackgroundColor(index, self.table.model().color_ABrowConflict, True)
        else:
            self.table.model().changeBackgroundColor(index, self.table.model().color_ABrowConflict, False)

    def getInvalidEPsForAB(self, ep):
        shorthand = self.epConfig.loc[self.epConfig['Emission Point'] == ep, "Shorthand"].item()
        shorthandSplit = shorthand.split('-')
        ab = shorthandSplit[1][-1]
        errorShorthands = []
        if ab == "A":
            shorthandSplit[1] = shorthandSplit[1][:-1] + 'B'
            shorthandSplit = shorthandSplit[:2]
            errorShorthands.append("-".join(shorthandSplit))
        else:
            shorthandSplit[1] = shorthandSplit[1][:-1] + 'A'
            shorthandSplit.append('R')
            errorShorthands.append("-".join(shorthandSplit))
            shorthandSplit[2] = 'L'
            errorShorthands.append("-".join(shorthandSplit))
        errorEPs = []
        for sh in errorShorthands:
            findEP = self.epConfig.loc[self.epConfig['Shorthand'] == sh, 'Emission Point']
            if len(findEP) > 0:
                errorEPs.append(findEP.item())
        return errorEPs

    def checkForInvalidEP_RL(self, ep):
        """ Check if ep has a Left or Right and disable that one in ep selector"""
        df = self.getActions()
        usedEPs = df['Emission Point'].unique()
        try:
            shorthand = self.epConfig.loc[self.epConfig['Emission Point'] == ep, "Shorthand"].item()
            # shorthand = df.loc[df['Emission Point'] == ep, "Shorthand"].item()
            shorthandSplit = shorthand.split("-")
            if len(shorthandSplit) >= 3: # check if it has R or L
                rl = shorthandSplit[2]
                if rl == 'R':
                    shorthand = shorthand[:-1]+'L'
                elif rl == 'L':
                    shorthand = shorthand[:-1]+'R'
                disableEP = self.epConfig.loc[self.epConfig['Shorthand'] == shorthand, 'Emission Point']
                if len(disableEP) == 1:  # check for R or L that needs to be disabled
                    disableEP = disableEP.item()
                    if type(disableEP) is str:
                        if ep not in usedEPs:
                            self.select_ep.setEPEnabled(disableEP, True)
                        else:
                            self.select_ep.setEPEnabled(disableEP, False)
        except ValueError as e:
            # print("Warning: Error in checkForInvalidEP_R/L: "+str(e))
            pass

    def showFMSpan(self, time, fmFlow):
        self.timeRect.setRect(int(time)-.1, -0.1, 1, fmFlow+.2)

    def calculateFlowRateStats(self, df: pd.DataFrame, flowrateUnit='SLPM'):
        maxTime = df["Timing"].max()
        uniqueEPS = df['Emission Point'].unique()
        epFlows = {ep: np.zeros(maxTime+1) for ep in uniqueEPS}
        for index, row in df.iterrows():
            epFlows[row['Emission Point']][row['Timing']:] = row['Flow Rate']
        epStats = {}
        for ep, val in epFlows.items():
            avg = Conversion.convert(sum(val)/len(val), RAW_UNIT, flowrateUnit)
            maxFlow = Conversion.convert(max(val), RAW_UNIT, flowrateUnit)
            count = np.count_nonzero(val)
            percent = count / len(val)
            epStats[ep] = {"max flow rate ("+flowrateUnit+")": maxFlow, "avg flow rate ("+flowrateUnit+")": avg, "percentEmitting": percent}
        return epStats

    def clicked_addEvent(self, ev):
        if self.epConfig is not None:
            ep = self.select_ep.getCurrentEP()
            flowLevel = int(self.input_flowLevel.value())  # get flow level
            flowTiming = self.input_flowTiming.value()  # get timing
            intent = self.input_intent.text()
            category = getEmissionCategory(self.input_category.currentText())
            if ep:
                fm = self.getFMfromEP(ep)
                self.addEPEvent(ep, flowLevel, flowTiming, fm, intent, category=category)
        self.updateGraphAndTable()
        self.setBoldEP(ep)

    def clicked_addLinkedEvent(self, ev):
        if self.epConfig is not None:
            ep = self.select_ep.getCurrentEP()
            flowLevel = int(self.input_flowLevel.value())
            linkID = int(self.input_linkedID.value())
            linkTime = int(self.input_linkedTiming.value())
            intent = self.input_intent.text()
            category = getEmissionCategory(self.input_category.currentText())
            if ep:
                flowmeter = self.getFMfromEP(ep)
                time = self.table.getTiming(linkID) + linkTime
                addedID = self.addEPEvent(ep, flowLevel, time, flowmeter, intent, category=category)
                if addedID:
                    self.table.linkEPEvent(addedID, linkID, linkTime)
            self.updateGraphAndTable()
            self.setBoldEP(ep)

    def removedEPSlot(self, removedEPs):
        for ep, time in removedEPs:
            self.checkForInvalidEP_RL(ep)

    def changeEventEP(self, eID):
        ep = self.select_ep.getCurrentEP()
        shorthand = self.epConfig.loc[self.epConfig['Emission Point'] == ep, "Shorthand"].item()
        cb = self.getCBfromEP(ep)
        self.getEPColor(ep)
        self.table.editEvent(eID, {"Emission Point": ep, "CB":cb, "Flow Meter": self.getFMfromEP(ep), "Shorthand": shorthand})
        self.updateGraphAndTable()

    def addEPEvent(self, ep, level, timing, flowmeter, intent, category=EmissionCategories.Fugitive):
        if self.selectedEP is None:
            self.selectedEP = ep
        self.lastID += 1
        maxlevel = self.getMaxFlowLevel(ep)
        if level > maxlevel:
            level = 0
        actionID = self.lastID
        flowrate = self.calculateFlowRate(ep, level)
        shorthand = self.epConfig.loc[self.epConfig['Emission Point'] == ep, "Shorthand"].item()
        color = self.getEPColor(ep)
        cb = self.getCBfromEP(ep)
        row = self.getRowfromEP(ep)
        newEventAdded = self.table.addEPEvent(actionID, ep, level, timing, flowrate, flowmeter, category.value, intent, shorthand, cb, row)
        self.checkForInvalidEP_RL(ep)
        if not newEventAdded:  # don't create new event ID if just editing existing event based on existing ep and timing
            self.lastID -= 1
            return False
        else:  # new event
            return self.lastID

    def calculateFlowRate(self, emissionPoint, flowlevel):
        try:
            controller = self.getCBfromEP(emissionPoint)
            pressure = float(self.pressuresConfig.loc[self.pressuresConfig['Controller'] == controller, "Pressure (psia)"].item())
            shorthand = self.epConfig.loc[self.epConfig['Emission Point'] == emissionPoint, 'Shorthand'].item()
            row = shorthand.split('-')[1][0]
            columns = getValveColumns(flowlevel)
            QTotal = 0
            for c in columns:
                ep = controller+".EV-"+str(row)+str(c)
                orifice = self.spansConfig.loc[self.spansConfig["Flow Name"] == ep, "Orifice"].item()
                cv = orificeToCv(float(orifice))
                qg = calculateQg(cv, pressure, self.val_atm, self.val_temp, self.val_sg)
                QTotal += qg
            return round(QTotal, 2)
        except Exception as e:
            print("Error when trying to calculate flow rate:", e)
            return 0

    def refreshFlowRates(self):
        with self.table.dfLock:
            df = self.table.getDF()
            flowrates = {}
            for eid, row in df.iterrows():
                flowrates[eid] = self.calculateFlowRate(row['Emission Point'], row['Flow Level'])
            self.table.setFlowRates(flowrates)
        self.updateGraphAndTable()
        self.setSelectedEP(self.selectedEP)

    def refreshFlowMeters(self):
        """ new fm config loaded """
        df = self.getActions()
        for index, row in df.iterrows():
            fm = self.getFMfromEP(row['Emission Point'])
            self.table.editEvent(index, {"Flow Meter": fm})
        self.updateGraphAndTable()

    def clearTable(self):
        self.table.clearTable()
        self.lastID = 0
        self.updateGraphAndTable()

    def resetIDs(self):
        self.lastID = self.table.resetIDs()
        self.updateGraphAndTable()

    def getEPColor(self, ep):
        color = self.epColors.get(ep)
        if not color:
            self.epColors[ep] = epToColor(ep)
            self.table.setEPColor(ep, self.epColors[ep])
        return color

    def saveTable(self):
        filename, _ = self.dialog.getSaveFileName(self, 'Save Experiment Table', self.savedir+"/.csv")
        if filename:
            self.getActions().to_csv(filename, index=True)

    def loadTable(self, path=None):
        if not path:
            path, _ = self.dialog.getOpenFileName(self, 'Load Experiment Table', self.savedir)
        if path:
            df = pd.read_csv(path, index_col=0, dtype={"Timing": np.int64, "Link ID": np.str, "Link Time": np.str})
            df['Link ID'] = pd.to_numeric(df['Link ID'], errors='coerce', downcast='integer')
            df['Link Time'] = pd.to_numeric(df['Link Time'], errors='coerce', downcast='integer')
            df['Link ID'] = self.convertToInt(df['Link ID'])
            df['Link Time'] = self.convertToInt(df['Link Time'])

            self.lastID = df.index[-1]
            self.table.setDF(df)
            self.updateGraphAndTable()

    def convertToInt(self, n):
        m = []
        for i in n:
            if math.isnan(i):
                m.append('')
            else:
                m.append(int(i))
        return m