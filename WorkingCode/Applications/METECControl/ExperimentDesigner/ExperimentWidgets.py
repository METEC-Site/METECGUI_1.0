import json
import os
import pandas as pd
from PyQt5 import QtWidgets as qtw, QtCore as qtc

from Applications.METECControl.GUI.ConfigSelectionWidget import ConfigSelectionWidget
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.DataFrameModel import DataFrameModel


class EditableConfig(qtw.QWidget):
    viewPos = (1, 1, 1, 3)
    loadFile = qtc.pyqtSignal()
    edited = qtc.pyqtSignal()

    def __init__(self, columns, view=None, labelText="", filepath="", hiddenColumns=None):
        qtw.QWidget.__init__(self)
        self.editable = False
        self.columns=columns
        if hiddenColumns is None:
            hiddenColumns = []
        self.hiddenColumns = hiddenColumns
        self.data = None
        self.hiddenData = None
        if view is None:
            view = qtw.QTableView()
            view.setModel(DataFrameModel(pd.DataFrame()))
            view.model().edited.connect(lambda x: self.edited.emit())
        self.view = view
        self.filepath = filepath
        self.labelText = labelText
        self.label = qtw.QLabel(text=labelText)
        self.setLayout(qtw.QGridLayout())
        self.layout().addWidget(self.label, 0, 1, 1, 3)
        self.layout().addWidget(self.view, *self.viewPos)
        self.button_toggleEdits = qtw.QPushButton(text="Enable Editing")
        self.button_toggleEdits.clicked.connect(self.toggleEditable)
        self.layout().addWidget(self.button_toggleEdits, 2, 1)
        self.button_load = qtw.QPushButton(text="Load")
        self.loadFile = self.button_load.clicked
        self.layout().addWidget(self.button_load, 2, 2)
        self.button_export = qtw.QPushButton(text="Export")
        self.layout().addWidget(self.button_export, 2, 3)
        self.button_export.clicked.connect(self.exportFile)

    def toggleEditable(self):
        if type(self.view) in (qtw.QTableView, qtw.QPlainTextEdit):
            if self.editable:
                self.editable = not self.editable
                if type(self.view) == qtw.QPlainTextEdit:
                    self.view.setReadOnly(True)
                elif type(self.view) == qtw.QTableView:
                    self.view.model().setEditableColumns(False)
                self.button_toggleEdits.setText("Enable Editing")
            else:
                self.editable = not self.editable
                if type(self.view) == qtw.QPlainTextEdit:
                    self.view.setReadOnly(False)
                elif type(self.view) == qtw.QTableView:
                    self.view.model().setEditableColumns(True)
                self.button_toggleEdits.setText("Disable Editing")

    def setData(self, data):
        if type(data) == dict:
            data = pd.DataFrame(data.items(), columns=self.columns)
        if type(data) == list:
            data = pd.DataFrame(data, columns=self.columns)
        self.hiddenData = data.get(self.hiddenColumns)
        self.setViewDF(data)

    def setViewDF(self, df):
        if type(self.view) == qtw.QTableView:
            visiblecolumns = list(self.columns)
            for h in self.hiddenColumns:
                visiblecolumns.remove(h)
            df = df.get(visiblecolumns)
            self.view.model().setDF(df)
            self.view.resizeColumnsToContents()

    def exportFile(self):
        if type(self.view) in (qtw.QTableView, qtw.QPlainTextEdit):
            ConfigSelectionWidget.saveView(self.filepath, self.view)

    def getView(self):
        return self.view

    def getExperimentConfigData(self):
        if type(self.view) == qtw.QPlainTextEdit:
            data = json.loads(self.view.toPlainText())
        else:
            try:
                data = self.view.model().getDataFrame().join(self.hiddenData)
            except:
                data = None
        return data

    def setFilepath(self, filepath):
        self.filepath = filepath
        path, name = os.path.split(filepath)
        self.label.setText(self.labelText + '\n' + name)


class EmissionPointSelector(qtw.QWidget):
    currentEPChanged = qtc.pyqtSignal(str)
    currentFiltersChanged = qtc.pyqtSignal(str, str)

    def __init__(self):
        qtw.QWidget.__init__(self)
        self.epConfig = None
        self.filterPad = qtw.QComboBox()
        self.filterPad.addItem("All")
        self.filterController = qtw.QComboBox()
        self.filterController.addItem("All")
        self.filterController.currentTextChanged.connect(self.filtersChanged)
        self.filterPad.currentTextChanged.connect(self.filtersChanged)
        self.epIndexList = []
        self.disabledEP = set()
        self.list = qtw.QListWidget()
        self.list.clicked.connect(self.epSelected)
        self.setLayout(qtw.QGridLayout())
        self.layout().addWidget(qtw.QLabel(text="Pad"), 0, 1)
        self.layout().addWidget(qtw.QLabel(text="Controller"), 0, 2)
        self.layout().addWidget(self.filterPad, 1, 1)
        self.layout().addWidget(self.filterController, 1, 2)
        self.layout().addWidget(self.list, 2, 1, 1, 2)

    def epSelected(self, ev):
        self.currentEPChanged.emit(self.list.currentItem().text())

    def filtersChanged(self, newFilterText=None):
        self.list.clear()
        self.epIndexList.clear()
        padFilter = self.filterPad.currentText()
        contFilter = self.filterController.currentText()
        self.currentFiltersChanged.emit(padFilter, contFilter)
        for index, row in self.epConfig.iterrows():
            if row['Emission Point'] != "NaN" and type(row['Emission Point']) is str:
                add = True
                pad = row["Emission Point"][0]
                cont = row['Emission Point'][1:row['Emission Point'].index('-')]
                if padFilter != "All" and pad != padFilter:
                    add = False
                if contFilter != "All" and cont != contFilter:
                    add = False
                if add:
                    item = qtw.QListWidgetItem(row['Emission Point'])
                    if row['Emission Point'] in self.disabledEP:
                        item.setFlags(item.flags() & ~ qtc.Qt.ItemIsEnabled)
                    self.list.addItem(item)
                    self.epIndexList.append(row['Emission Point'])

    def getFilters(self):
        return self.filterPad.currentText(), self.filterController.currentText()

    def getCurrentEP(self):
        if self.list.currentItem():
            return self.list.currentItem().text()

    def setSelectedEP(self, ep):
        try:
            i = self.epIndexList.index(ep)
            self.list.setCurrentRow(i)
        except:
            self.list.clearSelection()  # if it's not in the list that's ok because it is hidden due to filters.

    def setEPEnabled(self, ep, bool):
        listItems = self.list.findItems(ep, qtc.Qt.MatchExactly)
        if len(listItems) == 1:
            listItem = listItems[0]
            if bool:
                try:
                    self.disabledEP.remove(ep)
                    listItem.setFlags(qtc.Qt.ItemIsEnabled)
                except KeyError:
                    pass
            else:
                listItem.setFlags(listItem.flags() & ~ qtc.Qt.ItemIsEnabled)
                self.disabledEP.add(ep)

    def setEPConfig(self, epconfig:pd.DataFrame):
        self.epConfig = epconfig
        self.epIndexList.clear()
        self.disabledEP.clear()
        self.list.clear()
        for index, row in epconfig.iterrows():
            try:
                if type(row['Emission Point']) is str:
                    pad = row["Emission Point"][0]
                    controller = row['Emission Point'][1:row['Emission Point'].index('-')]
                    if self.filterPad.findText(pad) == -1:
                        self.filterPad.addItem(pad)
                    if self.filterController.findText(controller) == -1:
                        self.filterController.addItem(controller)
                    # self.list.addItem(row['Emission Point'])
                    # self.epIndexList.append(row['Emission Point'])
            except Exception as e:
                print(f"Error in EPConfig for emission point {row['Emission Point']}, row number {index+1}\n{e}")
        self.filtersChanged()