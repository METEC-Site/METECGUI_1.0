import queue

# from Applications.METECControl.GUI.RefactoredWidgets.ExperimentalControl.GSHQueue import GSHQueue
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc


class ExpQueue(qtw.QGroupBox):

    def __init__(self, name, title, parent, *args, **kwargs):
        qtw.QGroupBox.__init__(self, title, parent, *args)
        self.name = name
        self._addLayout()
        # self._addGSHLists()
        self._addActionWidget()

        self.updateTimer = qtc.QTimer()
        self.updateTimer.timeout.connect(self.checkTests)
        self.updateTimer.start(100)

    def _addActionWidget(self):
        self.actionLayout = qtw.QVBoxLayout()
        self.actionLayout.setContentsMargins(0, 0, 0, 0)
        self.actionsWidget = qtw.QWidget()
        self.actionsWidget.setLayout(self.actionLayout)
        self.mainLayout.addWidget(self.actionsWidget)

        self.deleteButton = qtw.QToolButton()
        self.deleteIcon = self.deleteButton.style().standardIcon(qtw.QStyle.SP_DialogCancelButton)
        self.deleteButton.setIcon(self.deleteIcon)

        self.actionLayout.addWidget(self.deleteButton)
        self.actionLayout.addStretch()

    def _addLayout(self):
        self.mainLayout = qtw.QHBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.mainLayout)

    def _addGSHLists(self):
        self.gsh1List = GSHQueue("GSH-1", None)
        self.mainLayout.addWidget(self.gsh1List)
        self.gsh2List = GSHQueue("GSH-2", None)
        self.mainLayout.addWidget(self.gsh2List)
        self.gsh3List = GSHQueue("GSH-3", None)
        self.mainLayout.addWidget(self.gsh3List)
        self.gsh4List = GSHQueue("GSH-4", None)
        self.mainLayout.addWidget(self.gsh4List)

    def getSelectedIDs(self):
        gsh1selected = self.gsh1List.getSelectedIDs()
        gsh2selected = self.gsh2List.getSelectedIDs()
        gsh3selected = self.gsh3List.getSelectedIDs()
        gsh4selected = self.gsh4List.getSelectedIDs()
        ids = [*gsh1selected, *gsh2selected, *gsh3selected, *gsh4selected]
        return ids

    def removeSelected(self):
        self.gsh1List.removeSelectedTest()
        self.gsh2List.removeSelectedTest()
        self.gsh3List.removeSelectedTest()
        self.gsh4List.removeSelectedTest()