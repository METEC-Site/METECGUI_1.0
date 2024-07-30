import PyQt5.QtCore as qtc
import PyQt5.QtWidgets as qtw
import pandas as pd
from Applications.METECControl.GUI.ConfigSelectionWidget import Configs, ConfigSelectionWidget
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.DataFrameModel import DataFrameModel
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.StopButton import StopButton
from Framework.BaseClasses.QtMixin import QtMixin
from Utils import TimeUtils as tu

ProcessGroups = {
    "PAD-1":{"button": None, "row":1, "col":0},
    "PAD-2":{"button": None, "row":1, "col":1},
    "PAD-3":{"button": None, "row":2, "col":0},
    "PAD-4":{"button": None, "row":2, "col":1},
    "PAD-5":{"button": None, "row":3, "col":0},
    "PAD-6":{"button": None, "row":3, "col":1},
    "PAD-7":{"button": None, "row":4, "col":0},
    "GMR-1":{"button": None, "row":4, "col":1}}

DEFAULT_EP_HEADERS_V1 = ["Pad", "Controller", "Valve Row", "Valve Position", "T Position", "Emission Point"] # old version
DEFAULT_EP_HEADERS_V2 = ["Shorthand", "Active", "Emission Point"] # updated version

class SidebarCommand(qtw.QFrame, QtMixin):

    def __init__(self, GUIInterface, name=None, parent=None, *args, **kwargs):
        QtMixin.__init__(self, GUIInterface, name, parent, *args, **kwargs)
        qtw.QFrame.__init__(self, parent)
        self.mainWidgetLayout = qtw.QVBoxLayout(self)
        self.setLayout(self.mainWidgetLayout)

        self.fileDialog = qtw.QFileDialog()
        self.headerPicker = HeaderSelector()
        self.configSelectionWidget = ConfigSelectionWidget(self.GUIInterface, self)
        self.epDF = None
        self.fmDF = None

        self.createShutdownButtons()
        self.createTabContainer()

        # self.createTestOverviewBox()
        # self.createNotesBox()
        # self.createStatusBox(self.deviceList)
        self.createFMConfigTab()
        self.createEPConfigTab()
        # self.createEventBox()
        # self.createCommandBox()
        # self.retranslateUi(self.parentObj)
        # QtCore.QMetaObject.connectSlotsByName(parent)
        self.setMinimumHeight(10)
        self.setMinimumWidth(10)
        self.setMaximumWidth(300)

        self.notConnectedItems = set()
        self.loadCurrentConfigs()

    def createShutdownButtons(self):
        self.shutdownBox = qtw.QGroupBox(self)
        self.shutdownBox.setTitle("ShutdownBox")
        self.shutdownButtonsLayout = qtw.QGridLayout(self.shutdownBox)

        self.shutdownSiteButton = StopButton('Site Stop', emitStrings=list(ProcessGroups.keys()))

        self.shutdownSiteButton.signalStop.connect(self.shutdownProcessGroup)
        self.shutdownButtonsLayout.addWidget(self.shutdownSiteButton, 0, 0, 1, 2)
        for processGroup, buttonInfo in ProcessGroups.items():
            btn = StopButton(processGroup + " Stop", emitStrings=[processGroup])
            btn.signalStop.connect(self.shutdownProcessGroup)
            self.shutdownButtonsLayout.addWidget(btn, buttonInfo['row'], buttonInfo['col'], 1, 1)
            buttonInfo['button'] = btn
        self.mainWidgetLayout.addWidget(self.shutdownBox)

    @qtc.pyqtSlot(str)
    def shutdownProcessGroup(self, processGroup):
        self.GUIInterface.shutdownProcessGroup(processGroup)

    def createTabContainer(self):
        self.tabWidget = qtw.QTabWidget(self)
        self.mainWidgetLayout.addWidget(self.tabWidget)

    def loadCurrentConfigs(self):
        curFM = self.GUIInterface.getSelectedSummary(Configs.FMconfig)
        if not curFM is None:
            self._loadNewFMConfigTable(curFM)
        curEP = self.GUIInterface.getSelectedSummary(Configs.EPconfig)
        if not curEP is None:
            self._loadNewEPConfigTable(curEP)

    def createFMConfigTab(self):
        fmConfigBox = qtw.QGroupBox(self)
        fmConfigBox.setTitle("FM Config")
        fmConfigBox.layout = qtw.QVBoxLayout(fmConfigBox)

        button_loadFMconfig = qtw.QPushButton()
        button_loadFMconfig.setText("Set FM config")
        button_loadFMconfig.clicked.connect(self._clicked_loadFMconfig)

        button_reloadFMconfig = qtw.QPushButton()
        button_reloadFMconfig.setText('Reload FM configs')
        button_reloadFMconfig.clicked.connect(self._clicked_reloadFMconfig)

        self.flowTable = qtw.QTableView(fmConfigBox)
        df = pd.DataFrame({"Controller": [], "Flowmeter ID": [], "Detected": []})
        self.flowModel = DataFrameModel(df)
        self.flowTable.setModel(self.flowModel)
        fmConfigBox.layout.addWidget(button_loadFMconfig)
        fmConfigBox.layout.addWidget(button_reloadFMconfig)
        fmConfigBox.layout.addWidget(self.flowTable)
        self.fmConfigBox = fmConfigBox
        self.tabWidget.addTab(fmConfigBox, "FM Config")

    def _clicked_reloadFMconfig(self):
        self.GUIInterface.updateSingleSummary(Configs.FMconfig)

    def _clicked_loadFMconfig(self):
        timestamp = self.configSelectionWidget.chooseConfig(Configs.FMconfig)
        try:
            self.GUIInterface.selectSummary(Configs.FMconfig, timestamp)
            table = self.GUIInterface.getSelectedSummary(Configs.FMconfig)
            self._loadNewFMConfigTable(table)
        except Exception as e:
            print(f'Cannot load clicked FM due to exception {e}')

    def _loadNewFMConfigTable(self, configTable):
        newDF = pd.DataFrame()
        newDF[['Controller', "Flowmeter ID"]] = configTable[['Controller', "Flowmeter ID"]]
        # self.flowModel = DataFrameModel(newDF)
        # self.flowTable.setModel(self.flowModel)
        self.flowModel.setDF(newDF)
        self.flowTable.resizeColumnsToContents()

    ### todo: check here, start of new additions.

    def createEPConfigTab(self):
        epConfigBox = qtw.QGroupBox(self)
        epConfigBox.setTitle("EP Config")
        epConfigBox.layout = qtw.QVBoxLayout(epConfigBox)
        self.button_epHeaderPicker = qtw.QPushButton(text="Pick headers")
        self.button_epHeaderPicker.clicked.connect(self.epHeaderPicker)

        button_loadEPconfig = qtw.QPushButton()
        button_loadEPconfig.setText("Load EP config")
        self.epPathLabel = qtw.QLabel("")
        button_loadEPconfig.clicked.connect(self._clicked_loadEPconfig)
        self.epTable = qtw.QTableView()
        self.epModel = DataFrameModel(pd.DataFrame())

        epConfigBox.layout.addWidget(button_loadEPconfig)
        epConfigBox.layout.addWidget(self.epPathLabel)
        epConfigBox.layout.addWidget(self.button_epHeaderPicker)
        epConfigBox.layout.addWidget(self.epTable)
        self.tabWidget.addTab(epConfigBox, "EP Config")
        self._clicked_loadEPconfig(tu.nowEpoch())
        self.reloadEPHeaders(self.headerPicker.getHeaders())

    def epHeaderPicker(self, event):
        if self.epDF is not None:
            headers = self.headerPicker.exec()
            self.reloadEPHeaders(headers)

    def reloadEPHeaders(self, headers):
            df = self.epDF.get(headers)
            self.epModel = DataFrameModel(df)
            self.epTable.setModel(self.epModel)
            self.epTable.resizeColumnsToContents()

    def _clicked_loadEPconfig(self, timestamp=None):
        if timestamp is None:
            timestamp = self.configSelectionWidget.chooseConfig(Configs.EPconfig)
        try:
            self.GUIInterface.selectSummary(Configs.EPconfig, timestamp)
            table = self.GUIInterface.getSelectedSummary(Configs.EPconfig)
            self._loadNewEPConfigTable(table)
        except Exception as e:
            print(f'Cannot load clicked EP due to exception {e}')

    def _loadNewEPConfigTable(self, configTable):
        self.epDF = configTable
        dfCopy = pd.DataFrame()
        try:
            dfCopy[DEFAULT_EP_HEADERS_V1] = configTable[DEFAULT_EP_HEADERS_V1]
            defaultEPHeaders = DEFAULT_EP_HEADERS_V1
        except:
            dfCopy[DEFAULT_EP_HEADERS_V2] = configTable[DEFAULT_EP_HEADERS_V2]
            defaultEPHeaders = DEFAULT_EP_HEADERS_V2
        # self.epModel = DataFrameModel(copy)
        # self.epTable.setModel(self.epModel)
        self.epModel.setDF(dfCopy)
        self.epTable.resizeColumnsToContents()
        headers = list(configTable.columns.values)
        self.headerPicker.setHeaders(headers, defaultEPHeaders)

    def _updateEPStateDetection(self, key, detected):
        """ should be called by handlePackage() when receiving state detection data """
        df = self.flowModel.getDataFrame()
        index = df[df['CB'] == key].index
        if len(index) == 1:
            index = index[0]
            df.loc[index, "Detected"] = detected
            if df.at[index, "Emission Point"] != df.at[index, "Detected"]:
                self.epModel.changeErrorRow(index, True)
            else:
                self.epModel.changeErrorRow(index, False)

    ### end of new additions

    def togglePopout(self, box: qtw.QTextEdit):
        if self.popout.isVisible():
            self.popout.geo_w = self.popout.width()
            self.popout.geo_h = self.popout.height()
            self.popout.box.setParent(self.popout.box.parentGroup)
            self.popout.hide()
            self.popout.box.parentGroup.layout.addWidget(self.popout.box)
        else:
            self.popout.box = box
            box.setParent(self.popout)
            box.setGeometry(0, 0, self.popout.geo_w, self.popout.geo_h)
            self.popout.show()

class HeaderSelector:

    def __init__(self):
        self.popout = qtw.QDialog()
        self.listView = qtw.QListWidget(self.popout)
        self.popout.setLayout(qtw.QVBoxLayout())
        self.popout.layout().addWidget(self.listView)
        self.confirmButton = qtw.QPushButton("Confirm")
        self.confirmButton.clicked.connect(self.updateHeaders)
        self.popout.layout().addWidget(self.confirmButton)
        self.headers = {}

    def setHeaders(self, headers, checkedHeaders):
        self.listView.clear()
        for header in headers:
            widget = qtw.QCheckBox(parent = self.listView, text=header)
            headerState = 0
            if header in checkedHeaders:
                headerState = 1
            widget.setChecked(bool(headerState))
            item = qtw.QListWidgetItem(parent=self.listView)
            item.setSizeHint(widget.sizeHint())
            self.headers[header] ={'widget': widget, "state":headerState}
            self.listView.addItem(item)
            self.listView.setItemWidget(item, widget)

    def getHeaders(self):
        return [h for h in self.headers if self.headers[h]['state']]

    # @qtc.pyqtSlot()
    def updateHeaders(self, torf):
        for headerName, headerInfo in self.headers.items():
            widget = headerInfo['widget']
            headerInfo['state'] = widget.isChecked()
            self.popout.done(torf)

    def exec(self):
        self.popout.exec()
        return self.getHeaders()