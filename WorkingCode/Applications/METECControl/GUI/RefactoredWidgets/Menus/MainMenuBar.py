import PyQt5.QtCore as qtc
import PyQt5.QtWidgets as qtw
from Applications.METECControl.GUI.ConfigSelectionWidget import Configs
from Framework.BaseClasses.QtMixin import QtMixin


class MainMenuBar(qtw.QMenuBar, QtMixin):

    def __init__(self, GUIInterface=None, name="MainMenuBar", parent=None, *args, **kwargs):
        qtw.QMenuBar.__init__(self)
        QtMixin.__init__(self, GUIInterface=GUIInterface, name=name, parent=parent, *args, **kwargs)

        # self.fileMenu = self.addMenu('File')  # uncomment when actions are added
        self.editMenu = self.addMenu('Edit')
        self._addEditMenuActions()
        self.viewMenu = self.addMenu('View')
        self._addViewMenuActions()
        # self.searchMenu = self.addMenu('Search')
        # self.toolsMenu = self.addMenu('Tools')
        # self.helpMenu = self.addMenu('Help')

##### FILE MENU

##### EDIT MENU
    def _addEditMenuActions(self):
        self.editAction_fmConfig = self.editMenu.addAction("Edit FM Config")
        self.editAction_epConfig = self.editMenu.addAction("Edit EP Config")
        self.editAction_expConfig= self.editMenu.addAction("Edit Experiment Config")
        self._editMapping = {
            self.editAction_fmConfig: Configs.FMconfig,
            self.editAction_epConfig: Configs.EPconfig,
            self.editAction_expConfig: Configs.FMconfig
        }
        self.editMenu.triggered.connect(self._editMenuActions)

    def _editMenuActions(self, action):
        # todo: revisit this after deciding how to edit configs in the Archiver.
        config = self._editMapping[action]
        filepath = self.GUIInterface.getConfigManager().chooseFile(config.value)
        if filepath:
            self.GUIInterface.emitConfigChanged(config, filepath, self.name)

##### VIEW MENU
    def _addViewMenuActions(self):
        self.viewAction_fmConfig = qtw.QAction("View FM Config", self.viewMenu)
        self.viewAction_epConfig = qtw.QAction("View EP Config", self.viewMenu)
        self.viewAction_expConfig= qtw.QAction("View Experiment Config", self.viewMenu)
        self.viewMenu.addAction(self.viewAction_fmConfig)
        self.viewMenu.addAction(self.viewAction_epConfig)
        self.viewMenu.addAction(self.viewAction_expConfig)
        self._viewMapping = {
            self.viewAction_fmConfig: Configs.FMconfig,
            self.viewAction_epConfig: Configs.EPconfig,
            self.viewAction_expConfig: Configs.ExperimentConfig
        }
        self.viewMenu.triggered.connect(self._viewMenuActions)

    def _viewMenuActions(self, action):
        cfgEnumVal = self._viewMapping[action]
        self.GUIInterface.getConfigManager().viewFile(self.GUIInterface.getConfigPath(cfgEnumVal), cfgEnumVal.value)

    @qtc.pyqtSlot(str)
    def fmConfigChangedSlot(self, filename):
        pass

    @qtc.pyqtSlot(str)
    def epConfigChangedSlot(self, filename):
        pass

##### SEARCH MENU

##### TOOLS MENU

##### HELP MENU