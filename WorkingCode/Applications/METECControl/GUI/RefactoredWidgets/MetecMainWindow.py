import logging

import PyQt5.QtCore as qtc
import PyQt5.QtWidgets as qtw
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.ScrollWidget import ScrollWidget
# from Applications.METECControl.GUI.RefactoredWidgets.ExperimentalControl.ExperimentContainer import ExpContainer
from Applications.METECControl.GUI.RefactoredWidgets.ExperimentalControl.Container import ExpContainer
from Applications.METECControl.GUI.RefactoredWidgets.GUITabs.GSH1Tab import GSH1Tab
from Applications.METECControl.GUI.RefactoredWidgets.GUITabs.GSH2Tab import GSH2Tab
from Applications.METECControl.GUI.RefactoredWidgets.GUITabs.GSH3Tab import GSH3Tab
from Applications.METECControl.GUI.RefactoredWidgets.GUITabs.GSH4Tab import GSH4Tab
from Applications.METECControl.GUI.RefactoredWidgets.GUITabs.METTab import METTab
from Applications.METECControl.GUI.RefactoredWidgets.GUITabs.TabManager import TabManager
from Applications.METECControl.GUI.RefactoredWidgets.Menus.MainMenuBar import MainMenuBar
from Applications.METECControl.GUI.RefactoredWidgets.SidebarCommandWidget import SidebarCommand
from Framework.BaseClasses.QtMixin import QtMixin
from Utils import QtUtils as qu


class MainWindow(qtw.QMainWindow, QtMixin):
    fmConfigUpdated = qtc.pyqtSignal(str)
    epConfigUpdated = qtc.pyqtSignal(str)
    windowClosedSignal = qtc.pyqtSignal()

    def __init__(self, GUIInterface, name="METECGUI", parent=None, updateInterval=1,
                 leftDim=100, topDim=100, widthDim=1000, heightDim=500):
        self.app = qu.getApp()
        QtMixin.__init__(self, GUIInterface=GUIInterface, name=name, parent=parent)
        qtw.QMainWindow.__init__(self, parent=parent)
        self.updateTimer = qtc.QTimer()
        self.updateTimer.timeout.connect(self.update)
        self.updateTimer.setSingleShot(False)
        self.updateInterval = updateInterval
        self.centralWidget = qtw.QWidget(parent=self)
        self.centralLayout = qtw.QGridLayout()
        self.centralWidget.setLayout(self.centralLayout)
        self.setCentralWidget(self.centralWidget)

        self.dimensions = {
            'left': leftDim,
            'top': topDim,
            'width': widthDim,
            'height': heightDim
        }

        self.initWindow()
        self.buildGUI()

    def start(self):
        self.updateTimer.start(self.updateInterval)

    def initWindow(self):

        self.setWindowTitle(self.label)
        # geometry = qtw.QDesktopWidget().screenGeometry()
        # self.dimensions['width'], self.dimensions['height'] = geometry.width(), geometry.height()
        self.setGeometry(*self.dimensions.values())
        self.move(self.frameGeometry().topLeft())
        self.show()

    def buildGUI(self):
        self._buildSidebar()
        self._buildTabManager()
        self._buildExperimentControl()
        self._buildGSH1()
        self._buildGSH2()
        self._buildGSH3()
        self._buildGSH4()
        # self._buildGMR()
        # self._buildMET()

    def _buildMainMenu(self):
        self.mainMenu = MainMenuBar(self.GUIInterface, parent=self)
        self.setMenuBar(self.mainMenu)

    def _buildSidebar(self):
        self.sidebar = SidebarCommand(GUIInterface=self.GUIInterface, name="SideBar", parent=self)
        self.centralLayout.addWidget(self.sidebar, 0, 0)

    def _buildTabManager(self):
        self.tabManager = TabManager(GUIInterface=self.GUIInterface, name="TabManager", parent=self)
        self.centralLayout.addWidget(self.tabManager, 0, 1)

    def _buildExperimentControl(self):
        self.experimentTab = ScrollWidget(GUIInterface=self.GUIInterface, name="Scroll", parent=self)
        self.experimentWidget = ExpContainer(GUIInterface=self.GUIInterface, name="Test Manager", parent=self)
        self.experimentTab.addWidget(self.experimentWidget)
        self.tabManager.addTab(self.experimentTab, "Experiments")

    def _buildGSH1(self):
        self.GSH1Tab = ScrollWidget(GUIInterface=self.GUIInterface, name="GSH-1", parent=self)
        self.GSH1TabWidget = GSH1Tab(GUIInterface=self.GUIInterface, name="GSH-1-Tab", parent=self)
        self.GSH1Tab.addWidget(self.GSH1TabWidget)
        self.tabManager.addTab(self.GSH1Tab, "GSH-1")

    def _buildGSH2(self):
        self.GSH2Tab = ScrollWidget(GUIInterface=self.GUIInterface, name="GSH-2", parent=self)
        self.GSH2TabWidget = GSH2Tab(GUIInterface=self.GUIInterface, name="GSH-2-Tab", parent=self)
        self.GSH2Tab.addWidget(self.GSH2TabWidget)
        self.tabManager.addTab(self.GSH2Tab, "GSH-2")

    def _buildGSH3(self):
        self.GSH3Tab = ScrollWidget(GUIInterface=self.GUIInterface, name="GSH-3", parent=self)
        self.GSH3TabWidget = GSH3Tab(GUIInterface=self.GUIInterface, name="GSH-3-Tab", parent=self)
        self.GSH3Tab.addWidget(self.GSH3TabWidget)
        self.tabManager.addTab(self.GSH3Tab, "GSH-3")

    # def _buildGMR(self):
    #     self.GMRTab = ScrollWidget(GUIInterface=self.GUIInterface, name="GMR", parent=self)
    #     self.GMRTabWidget = GMRTab(GUIInterface=self.GUIInterface, name="GMR-Tab", parent=self)
    #     self.GMRTab.addWidget(self.GMRTabWidget)
    #     self.tabManager.addTab(self.GMRTab, "GMR")

    # def _buildMET(self):
    #     self.METTab = ScrollWidget(GUIInterface=self.GUIInterface, name="MET", parent=self)
    #     self.METTabWidget = METTab(GUIInterface=self.GUIInterface, name="MET-Tab", parent=self)
    #     self.METTab.addWidget(self.METTabWidget)
    #     self.tabManager.addTab(self.METTab, "MET")

    def _buildGSH4(self):
        self.GSH4Tab = ScrollWidget(GUIInterface=self.GUIInterface, name="GSH-4", parent=self)
        self.GSH4TabWidget = GSH4Tab(GUIInterface=self.GUIInterface, name="GSH-4-Tab", parent=self)
        self.GSH4Tab.addWidget(self.GSH4TabWidget)
        self.tabManager.addTab(self.GSH4Tab, "GSH-4")

    # def _buildGMR(self):
    #     self.GMRTab = ScrollWidget(GUIInterface=self.GUIInterface, name="GMR", parent=self)
    #     self.GMRTabWidget = GMRTab(GUIInterface=self.GUIInterface, name="GMR-Tab", parent=self)
    #     self.GMRTab.addWidget(self.GMRTabWidget)
    #     self.tabManager.addTab(self.GMRTab, "GMR")

    def _buildMET(self):
        self.METTab = ScrollWidget(GUIInterface=self.GUIInterface, name="MET", parent=self)
        self.METTabWidget = METTab(GUIInterface=self.GUIInterface, name="MET-Tab", parent=self)
        self.METTab.addWidget(self.METTabWidget)
        self.tabManager.addTab(self.METTab, "MET")

    def update(self):
        qtw.QMainWindow.update(self)

    def closeEvent(self,event, *args, **kwargs):
        close = qtw.QMessageBox.question(self, "QUIT", "Are you sure want to stop process?",
                                         qtw.QMessageBox.Yes | qtw.QMessageBox.No, qtw.QMessageBox.No)
        if close == qtw.QMessageBox.Yes:
            event.accept()
            # MainWindow.closeEvent(self, event, *args, **kwargs)
            self.windowClosedSignal.emit()
            logging.info('closing Main window')
        else:
            event.ignore()

    def newConfigPath(self, config, path):
        pass
        # if config == Configs.FMconfig:
            # self.sidebar.loadFMconfigFile(path)