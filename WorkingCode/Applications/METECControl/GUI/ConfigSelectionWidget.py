from enum import Enum

import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.DataFrameModel import DataFrameModel

import pandas as pd # NOTE: pandas writing and reading excel also needs packages 'xlrs' and 'openpyxl'

########## https://doc.qt.io/qt-5/modelview.html
# https://doc.qt.io/qtforpython/overviews/model-view-programming.html
from Framework.BaseClasses.SummaryFileManager import summaryDateTimeToEpoch


class Configs(Enum):
    ReaderConfig = "ReaderConfig"
    GCConfig = "GCConfig"
    FMconfig = "FMConfig"
    EPconfig = "EPConfig"

class ConfigSelector(qtw.QListWidget):
    def __init__(self, GUIInterface, parent=None):
        qtw.QListWidget.__init__(self, parent)
        self.GUIInterface = GUIInterface
        self.currentItems = {}
        self.configKey = None

    def setConfigKey(self, configKey):
        self.clear()
        self.configKey = configKey
        configDF = self.GUIInterface.getSummaryOverview(configKey)
        for inx in configDF.index:
            row = configDF.iloc[inx]
            filename = row['Filename']
            timestamp = summaryDateTimeToEpoch(row["RecordDate"], row['RecordTime'])
            lwi = qtw.QListWidgetItem(str(filename), self)
            self.addItem(lwi)
            self.currentItems[timestamp] = lwi

    def getCurrentTS(self, item):
        return list(filter(lambda x: self.currentItems[x]==item, self.currentItems.keys()))[0]

    def removeItems(self):
        for timestamp in list(self.currentItems.keys()):
            item = self.currentItems.pop(timestamp)
            oldItem = self.takeItem(item)
            try:
                oldItem.deleteLater()
                del oldItem
            except Exception as e:
                print(f'Couldn\'t delete item widget from config selector due to exception {e}.')


class ConfigSelectionWidget(qtc.QObject):

    def __init__(self, GUIInterface, parent=None):
        qtc.QObject.__init__(self, parent)
        self.GUIInterface = GUIInterface

        self.configPreview = qtw.QDialog() # popout is the window
        self.configPreview.setGeometry(100, 100, 1000, 800)
        self.configPreview.setLayout(qtw.QGridLayout())

        self.selectConfigLabel = qtw.QLabel("Select {}")
        self.selectConfigLabel.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)
        self.currentView = DataFrameModel(pd.DataFrame())
        self.plainTextView = qtw.QPlainTextEdit(None)
        self.plainTextView.setReadOnly(False)
        self.currentView = self.plainTextView

        self.configList = ConfigSelector(self.GUIInterface)
        self.configList.currentItemChanged.connect(self.updateConfigBox)

        self.configPreview.layout().addWidget(self.configList, 1, 1)
        self.configPreview.layout().addWidget(self.currentView, 1, 2)

        self.confirmButtons = qtw.QWidget()
        self.confirmButtons.setLayout(qtw.QHBoxLayout())
        self.confirmButtons.buttonCancel = qtw.QPushButton(text="Cancel")
        self.confirmButtons.buttonConfirm = qtw.QPushButton(text="Confirm")
        self.confirmButtons.layout().addWidget(self.confirmButtons.buttonCancel)
        self.confirmButtons.layout().addWidget(self.confirmButtons.buttonConfirm)
        self.confirmButtons.buttonCancel.clicked.connect(self.cancelWindow)
        self.confirmButtons.buttonConfirm.clicked.connect(self.selectionConfirmed)

        self.configPreview.layout().addWidget(self.confirmButtons, 2, 1)

    @qtc.pyqtSlot(bool)
    def selectionConfirmed(self, event):
        self.configPreview.done(1) # 1 will be used later on to signal that the confirm button was selected.

    @qtc.pyqtSlot(bool)
    def cancelWindow(self, event):
        self.configPreview.done(0) # 1 will be used later on to signal that the cancel button was selected.

    def updateConfigBox(self, currentItem, previousItem):
        if currentItem:
            newTimestamp = self.configList.getCurrentTS(currentItem)
            cfgKey = self.configList.configKey
            thisSummary = self.GUIInterface.getSummaryAtTimestamp(cfgKey, newTimestamp)
            dfModel = self.getView(thisSummary, False)
            self._swapViewWidget(dfModel)
            self.selectedTimestamp = newTimestamp

    def chooseConfig(self, configKey):
        self.configPreview.setWindowTitle(configKey.value)
        self.configList.setConfigKey(configKey)
        ret = self.configPreview.exec()
        if ret:
            return self.selectedTimestamp
        return None

    @staticmethod
    def getView(config, editable):
        view = ConfigSelectionWidget.getDataFrameView(config, editable)
        view.resizeColumnsToContents()
        return view

    @staticmethod
    def getDataFrameView(config, editableColumns=None):
        # todo: check that this is correct for the dataframe, csvs, and dicts available to the config.
        view = qtw.QTableView()
        df = None
        if isinstance(config, pd.DataFrame):
            df = config
        if isinstance(config, list):
            df = pd.DataFrame(config)
        if isinstance(config, dict):
            df = pd.DataFrame(config, columns=config.keys())

        model = DataFrameModel(df, editableColumns=editableColumns)
        view.setModel(model)
        return view

    def _swapViewWidget(self, view):
        self.currentView.setParent(None)
        self.configPreview.layout().removeWidget(self.currentView)
        self.configPreview.layout().addWidget(view, 1, 2)
        view.setParent(self.configPreview)
        self.currentView.deleteLater()
        self.currentView = view
