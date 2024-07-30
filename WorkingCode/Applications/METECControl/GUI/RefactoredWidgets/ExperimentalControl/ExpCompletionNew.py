from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc

from Applications.METECControl.TestSuite.Deploying.Deploy import ScriptWidget
from Utils.QtUtils import CustomQTLock

class ExpCompletion(qtw.QGroupBox):
    def __init__(self, GUIInterface, name, title, parent):
        qtw.QGroupBox.__init__(self, title, parent)
        self.GUIInterface = GUIInterface
        self.compLock = CustomQTLock()
        self.name = name
        self.completedTests = []
        self._addLayout()
        self._addListWidget()

    def _addLayout(self):
        self.mainLayout = qtw.QHBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.mainLayout)

    def _addListWidget(self):
        self.listWidget = qtw.QListWidget()
        self.mainLayout.addWidget(self.listWidget)

    @qtc.pyqtSlot(ScriptWidget)
    def acceptTest(self, scriptWidget):
        with self.compLock:
            sw = self.parent().getWidget(scriptWidget)
            if not sw is None:
                self.completedTests.append(sw)
                self.listWidget.addItem(sw)