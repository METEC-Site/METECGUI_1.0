from threading import RLock

import pandas as pd
from Applications.METECControl.ExperimentDesigner.DesignerConfigs import EmissionCategories, TABLE_COLUMNS
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.DataFrameModel import DataFrameModel
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
from PyQt5 import QtWidgets as qtw
from PyQt5.QtCore import Qt
from Utils import Conversion


class EventsModel(DataFrameModel):

    color_epConflict = qtg.QColor(255, 90, 90)
    color_ABrowConflict = qtg.QColor(255,200,0)
    color_link = qtg.QColor(50,180,255)

    def __init__(self, df):
        DataFrameModel.__init__(self, df)
        self.epColors = {}
        self.boldFont = qtg.QFont()
        self.boldFont.setBold(True)
        self.eventsBackgroundColors = {}

    def setColor(self, ep, r, g, b):
        self.epColors[ep] = qtg.QBrush(qtg.QColor(r,g,b))

    def changeBackgroundColor(self, id, color:qtg.QColor, bool):
        if color.rgb() not in self.eventsBackgroundColors.keys():
            self.eventsBackgroundColors[color.rgb()] = []
        if bool:
            self.eventsBackgroundColors[color.rgb()].append(id)
        elif id in self.eventsBackgroundColors[color.rgb()]:
            self.eventsBackgroundColors[color.rgb()].remove(id)

    def setLinkedRows(self, indexes: list):
        self.eventsBackgroundColors[self.color_link] = indexes

    def data(self, index: qtc.QModelIndex, role=qtc.Qt.DisplayRole):
        row = index.row()
        col = index.column()
        if index.isValid():
            if role == qtc.Qt.DisplayRole:
                val = self._df.iloc[row, col]
                return str(val)
            if role == Qt.BackgroundRole:
                eventID = self._df.iloc[row].name
                if col == 0:
                    return qtg.QBrush(self.epColors.get(self._df.iloc[row,0]))
                for color, indexes in self.eventsBackgroundColors.items():
                    if eventID in indexes:
                        return qtg.QBrush(qtg.QColor(color))

    def setData(self, index: qtc.QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if role == Qt.EditRole and index.isValid() and value:
            self._df.iloc[index.row(),index.column()] = value
            self.edited.emit(index.row(), index.column(), value)
            return True
        return False

    def headerData(self, section: int, orientation: qtc.Qt.Orientation=qtc.Qt.Horizontal, role: int = qtc.Qt.DisplayRole):
        if orientation == qtc.Qt.Horizontal:
            if role == qtc.Qt.DisplayRole:
                return self._df.columns[section]
            if role == qtc.Qt.FontRole:
                return self.boldFont
            if role == Qt.BackgroundRole:
                return qtg.QBrush(qtg.QColor(89, 161, 96))
        if orientation == qtc.Qt.Vertical and role == qtc.Qt.DisplayRole:
            return str(self._df.iloc[section].name)

    def clearBackgrounds(self, color:qtg.QColor):
        self.eventsBackgroundColors[color.rgb()] = []


class ComboBoxItemDelegate(qtw.QStyledItemDelegate):

    def __init__(self, items):
        qtw.QStyledItemDelegate.__init__(self)
        self.items = items

    def createEditor(self, QWidget, QStyleOptionViewItem, QModelIndex):
        box = qtw.QComboBox(QWidget)
        box.addItems(self.items)
        return box

    def setModelData(self, QWidget:qtw.QComboBox, QAbstractItemModel, QModelIndex):
        QAbstractItemModel.setData(QModelIndex, QWidget.currentText(), qtc.Qt.EditRole)

    def setEditorData(self, QWidget, QModelIndex):
        currentText = str(QModelIndex.data(qtc.Qt.DisplayRole))
        index = QWidget.findText(currentText)
        QWidget.setCurrentIndex(index)


class EventsTable(qtw.QTableView):
    dataChanged = qtc.pyqtSignal()  # emitted when flow rate of any row changes by
    flowLevelChanged = qtc.pyqtSignal(int, str, int, int)  # emitted when editing table directly
    colorChanged = qtc.pyqtSignal(str, tuple)
    removedEPs = qtc.pyqtSignal(list)
    changeEP = qtc.pyqtSignal(int)

    def __init__(self, menubar, rawUnit):
        qtw.QTableView.__init__(self)
        self.dfLock = RLock()
        self.columns = list(TABLE_COLUMNS)
        self.epConfig = None
        self.fmConfig = None
        self.spansConfig = None
        self.hiddenColumns = ['Shorthand', 'CB', 'Row']
        self.df = pd.DataFrame(columns=self.columns)
        for c in self.hiddenColumns:
            self.columns.remove(c)
        self.displayDF = None
        self.filters = None, None
        self.rawUnit = rawUnit
        self.unit = "SLPM"
        self.setSortingEnabled(True)
        self.sortColumn = "Timing"
        self.sortByColumn(self.columns.index(self.sortColumn), qtc.Qt.AscendingOrder)
        self.setModel(EventsModel(pd.DataFrame(columns=self.columns)))
        self.model().changedSortingColumn.connect(self.setSortingColumn)
        # menu
        self.colorDialog = qtw.QColorDialog()
        self.menu = qtw.QMenu()
        self.menu.triggered.connect(self.menuActions)
        self.action_delete = self.menu.addAction("Delete")
        self.action_setColor = self.menu.addAction("Set Color")
        self.action_setEP = self.menu.addAction("Set to Selected EP")
        self.menu.addSection("Link")
        self.menuLinkWidget = qtw.QWidget()
        self.menuLinkID = qtw.QSpinBox()
        self.menuLinkID.setRange(0,9999999)
        self.menuLinkDiff = qtw.QSpinBox()
        self.menuLinkDiff.setRange(-999999, 999999)
        self.menuLinkWidget.setLayout(qtw.QGridLayout())
        self.menuLinkWidget.layout().addWidget(qtw.QLabel(text="ID"), 1, 1)
        self.menuLinkWidget.layout().addWidget(self.menuLinkID, 1, 2)
        self.menuLinkWidget.layout().addWidget(qtw.QLabel(text="Diff"), 2, 1)
        self.menuLinkWidget.layout().addWidget(self.menuLinkDiff, 2, 2)
        self.menuLinkWidgetAction = qtw.QWidgetAction(self.menu)
        self.menuLinkWidgetAction.setDefaultWidget(self.menuLinkWidget)
        self.menu.addAction(self.menuLinkWidgetAction)
        self.action_link = self.menu.addAction("Set Link")
        self.action_removeLink = self.menu.addAction("Remove Link")
        self.menu.addSection("Shift")
        self.shiftSpinbox = qtw.QSpinBox()
        self.shiftSpinbox.setRange(-99999999,99999999)
        shiftSpinBoxActionWidget = qtw.QWidgetAction(self.menu)
        shiftSpinBoxActionWidget.setDefaultWidget(self.shiftSpinbox)
        self.menu.addAction(shiftSpinBoxActionWidget)
        self.action_shift = self.menu.addAction("Apply shift")

        self.model().setEditableColumns([self.columns.index('Flow Level'), self.columns.index("Timing"), self.columns.index("Emission Category"), self.columns.index("Intent")])
        self.model().edited.connect(self.tableEdited)

        comboDelegate = ComboBoxItemDelegate(list(map(lambda x: x.value, EmissionCategories)))
        self.setItemDelegateForColumn(self.columns.index('Emission Category'), comboDelegate)

    def setDF(self, df):
        with self.dfLock:
            # set master DataFrame
            self.df = df

    def setEPConfig(self, df):
        self.epConfig = df

    def updateTable(self):
        # set displayed DataFrame
        displayDF = self.df.copy()
        if self.filters != (None, None):
            displayDF = self.applyFilters(displayDF, *self.filters)
        displayDF = displayDF.get(self.columns)
        displayDF = self.applyUnit(displayDF, self.unit)
        displayDF = displayDF.sort_values([self.sortColumn, 'Emission Point'])
        self.model().setDF(displayDF)

    def getDF(self) -> pd.DataFrame:
        with self.dfLock:
            return self.df

    def getDisplayDF(self) -> pd.DataFrame:
        return self.model().getDataFrame()

    def getPreCalEvents(self):
        with self.dfLock:
            df = self.getDF()
            return list(df.loc[df['Emission Category'] == EmissionCategories.PreTest.value].index)

    def getPostCalEvents(self):
        with self.dfLock:
            df = self.getDF()
            return list(df.loc[df['Emission Category'] == EmissionCategories.PostTest.value].index)

    def setEPColor(self, ep, color):
        self.model().setColor(ep, *color)

    def setFilters(self, pad, controller):
        if not pad and not controller:
            self.filters = (None, None)
            self.setDF(self.df)
        else:
            self.filters = (pad, controller)
            self.setDF(self.df)

    def applyFilters(self, df, pad, controller):
        # columns = list(df.columns)
        # old
        df['pad'] = [cb[3] for cb in df['CB']]
        df['controller'] = [cb[4] for cb in df['CB']]
        df = df.loc[( (df['pad'] == pad) | (pad == 'All') ) & ( (controller == "All") | (df['controller'] == controller) )]
        del df['pad']
        del df['controller']
        return df

    def setUnit(self, unit):
        if not unit =='':
            self.unit = unit
        self.setDF(self.df)

    def applyUnit(self, df: pd.DataFrame, unit):
        for index, row in df.iterrows():
            df.loc[index, 'Flow Rate'] = round(Conversion.convert(row['Flow Rate'], self.rawUnit, unit), 2)
            df.loc[index, 'Total FM Flow'] = round(Conversion.convert(row['Total FM Flow'], self.rawUnit, unit), 2)
        return df

    def tableEdited(self, row, column, value):
        with self.dfLock:
            displayDF = self.model().getDataFrame()
            eID = displayDF.iloc[row].name
            editedColumn = self.columns[column]
            error = False
            if not error:
                self.editEvent(eID, {editedColumn: value})

        self.dataChanged.emit()  # updates graph

    def setFlowRates(self, flowrates):
        """ used outside ActionsTable class so does not emit dataChanged"""
        with self.dfLock:
            df = self.getDF()
            for index, fr in flowrates.items():
                df.loc[index, "Flow Rate"] = fr
            self.setDF(df)

    def contextMenuEvent(self, e: qtg.QContextMenuEvent) -> None:
        qtw.QTableView.contextMenuEvent(self, e)
        self.menu.popup(e.globalPos())

    def menuActions(self, action):
        with self.dfLock:
            df = self.getDF()
            displayDF = self.model().getDataFrame()
            row = self.currentIndex().row()
            col = self.currentIndex().column()
            if len(displayDF) > 0:
                selectedID = displayDF.iloc[row].name
                if action == self.action_delete:
                    sIDs = [displayDF.iloc[sIndex.row()].name for sIndex in self.selectedIndexes()]
                    removedEPs = [(df.loc[eid, 'Emission Point'], df.loc[eid, 'Timing']) for eid in sIDs]
                    df = df.drop(sIDs)
                    for eid in sIDs:
                        for eventID in list(df.loc[df['Link ID'] == eid].index):  # remove links for all events linked to now deleted event
                            self.removeLink(df, eventID)
                    self.setDF(df)
                    self.dataChanged.emit()
                    self.removedEPs.emit(removedEPs)  # used by ep_selector to re-enable a new potentially allowed EP
                if action == self.action_link:
                    linkToID = self.menuLinkID.value()
                    linkDiff = self.menuLinkDiff.value()
                    self.linkEPEvent(selectedID, linkToID, linkDiff)
                    self.dataChanged.emit()
                if action == self.action_removeLink:
                    self.removeLink(df, selectedID)
                    self.dataChanged.emit()
                if action == self.action_shift:
                    for modelIndex in self.selectedIndexes():
                        shiftRow = modelIndex.row()
                        shiftID = displayDF.iloc[shiftRow].name
                        df.loc[shiftID, 'Timing'] += self.shiftSpinbox.value()
                        self.dataChanged.emit()
                if action == self.action_setColor:
                    ep = displayDF.loc[selectedID, "Emission Point"]
                    rgbTuple = self.colorDialog.getColor(self.model().epColors.get(ep).color()).getRgb()[0:3]
                    self.setEPColor(ep,rgbTuple)
                    self.colorChanged.emit(ep,rgbTuple)
                if action == self.action_setEP:
                    self.changeEP.emit(selectedID)

    def getTiming(self, eID):
        return self.getDF().loc[eID, "Timing"]

    def addEPEvent(self, id, ep, level, timing, flowRate, flowMeter, category, intent, shorthand, cb, row):
        with self.dfLock:
            df = self.getDF()
            foundID = None
            findExistingDP = df.loc[(df['Emission Point'] == ep) & (df['Timing'] == timing)]
            if id in df.index:
                foundID = id
            elif len(findExistingDP) > 0:  # exists so replace
                foundID = findExistingDP.index[0]
            if foundID:
                changes = {
                    "Flow Level": level,
                    "Flow Rate": flowRate,
                    "Emission Category": category,
                    "Intent": intent,
                    'CB': cb
                }
                self.editEvent(foundID, changes)
                return False
            else:
                newRow = pd.DataFrame([[ep, level, timing, flowRate, "", "", flowMeter, 0, category, intent, shorthand, cb, row]], index=[id],
                                      columns=self.columns+self.hiddenColumns)
                df = pd.concat([df, newRow], sort=True)
                self.setDF(df)
                return True

    def editEvent(self, eID, changes):
        """ handles casting of changes to int or float or whatever needed
        as well as all other changes needed by editing values in the table"""
        with self.dfLock:
            df = self.getDF()
            for column, value in changes.items():
                if column == 'Timing':
                    try:
                        value = int(value)
                        df.loc[eID, column] = value
                        if df.loc[eID, 'Link ID'] != "":
                            self.removeLink(df, eID)
                        self._updateLinkedTimings(df, eID, value)
                    except ValueError:
                        pass # don't set the value if it's not an integer
                elif column == 'Flow Level':
                    try:
                        value = int(value)
                        oldLevel = int(df.loc[eID, column])
                        df.loc[eID, column] = value
                        self.flowLevelChanged.emit(eID, df.loc[eID, "Emission Point"], value, oldLevel)
                    except ValueError:
                        pass # don't set the value if it's not an integer
                elif column == "Emission Point":
                    df.loc[eID, column] = value
                    self.flowLevelChanged.emit(eID, value, df.loc[eID, "Flow Level"], 0)
                else:
                    df.loc[eID, column] = value
            self.setDF(df)

    def setSortingColumn(self, col):
        self.sortColumn = col

    def recalculateAllFlowMeterRates(self):
        with self.dfLock:
            df = self.getDF()
            for fm in df['Flow Meter'].unique():
                df = self.recalculateFlowMeterRates(df, fm)
            self.setDF(df)

    def recalculateFlowMeterRates(self, df, fm):
        fmDF = df.loc[df['Flow Meter'] == fm]
        epFlows = {ep:0 for ep in fmDF['Emission Point'].unique()}
        events = fmDF.groupby("Timing")
        for i, timeEvent in events:
            for eid, epEvent in timeEvent.iterrows():
                epFlows[epEvent['Emission Point']] = epEvent['Flow Rate']
            df.loc[(df['Timing'] == epEvent['Timing']) & (df['Flow Meter'] == fm), "Total FM Flow"] = round(sum(epFlows.values()),2)
        return df

    def _updateLinkedTimings(self, df, eid, newTime):
        """ returns df with all event links completed, should probably setDF and emit dataChanged after returning"""
        df.loc[eid, 'Timing'] = newTime
        linkedEvents = list(df.loc[df['Link ID'] == eid].index)
        for eventID in linkedEvents:
            timeDiff = df.loc[eventID, 'Link Time']
            df = self._updateLinkedTimings(df, eventID, newTime+timeDiff)
        return df

    def linkEPEvent(self, linkedID, linkedToID, timeDiff):
        with self.dfLock:
            df = self.getDF()
            newTime = df.loc[linkedToID, "Timing"] + timeDiff
            df.loc[linkedID, "Link ID"] = int(linkedToID)
            df.loc[linkedID, "Link Time"] = int(timeDiff)
            df = self._updateLinkedTimings(df, linkedID, newTime)
            self.setDF(df)

    def removeLink(self, df, eID):
        df.loc[eID, 'Link ID'] = ""
        df.loc[eID, 'Link Time'] = ""

    def clearTable(self):
        df = self.getDF()
        df = df.drop(df.index)
        self.setDF(df)

    def resetIDs(self):
        df = self.getDF()
        df = df.set_index(pd.Index(range(1,len(df)+1)), drop=True)
        self.setDF(df)
        return len(df)

    def mousePressEvent(self, e: qtg.QMouseEvent) -> None:
        qtw.QTableView.mousePressEvent(self, e)
        # if e.button() == qtc.Qt.RightButton:

    def setModel(self, model:EventsModel):
        qtw.QTableView.setModel(self, model)

    def model(self) -> EventsModel:
        return qtw.QTableView.model(self)