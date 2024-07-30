from Applications.METECControl.TestSuite.Deploying.Deploy import ScriptWidget
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from Utils.QtUtils import CustomQTLock


class ExpQueue(qtw.QGroupBox):
    runTest = qtc.pyqtSignal(ScriptWidget)
    unqueueTest = qtc.pyqtSignal(ScriptWidget)

    def __init__(self, GUIInterface, name, title, parent, *args, **kwargs):
        qtw.QGroupBox.__init__(self, title, parent, *args)
        self.qLock = CustomQTLock()
        self.GUIInterface = GUIInterface
        self.name = name
        self.GSH1pendingTest = None
        self.GSH2pendingTest = None
        self.GSH3pendingTest = None
        self.GSH4pendingTest = None
        self.GSH1Queue = []
        self.GSH2Queue = []
        self.GSH3Queue = []
        self.GSH4Queue = []
        self._addLayout()
        self._addListWidget()
        self._addActionWidget()

        self.GSH1okToSend = True
        self.GSH2okToSend = True
        self.GSH3okToSend = True
        self.GSH4okToSend = True

        self.updateTimer = qtc.QTimer()
        self.updateTimer.timeout.connect(self.checkTests)
        self.updateTimer.start(100)

    def checkTests(self):
        with self.qLock:
            # have to check if it is OK to send and remove first,
            # because two listwidgetitems cannot exist in two different lists at once.
            if self.GSH1okToSend and len(self.GSH1Queue) > 0:
                # NOTE: items removed from this list will NOT be removed from Qt automatically.
                first = self.GSH1Queue[0]
                self.GSH1Queue.remove(first)
                gsh1inx = self.listWidget.row(first)
                scriptWidget = self.listWidget.takeItem(gsh1inx)
                if isinstance(scriptWidget, ScriptWidget):
                    self.GSH1pendingTest = scriptWidget
            if self.GSH1pendingTest:
                self.GSH1okToSend = False
                self.parent().acceptWidget(self.GSH1pendingTest)
                self.runTest.emit(self.GSH1pendingTest)
                self.GSH1pendingTest = None

            if self.GSH2okToSend and len(self.GSH2Queue) > 0:
                # NOTE: items removed from this list will NOT be removed from Qt automatically.
                first = self.GSH2Queue[0]
                self.GSH2Queue.remove(first)
                gsh2inx = self.listWidget.row(first)
                scriptWidget = self.listWidget.takeItem(gsh2inx)
                if isinstance(scriptWidget, ScriptWidget):
                    self.GSH2pendingTest = scriptWidget
            if self.GSH2pendingTest:
                self.GSH2okToSend = False
                self.parent().acceptWidget(self.GSH2pendingTest)
                self.runTest.emit(self.GSH2pendingTest)
                self.GSH2pendingTest = None

            if self.GSH3okToSend and len(self.GSH3Queue) > 0:
                # NOTE: items removed from this list will NOT be removed from Qt automatically.
                first = self.GSH3Queue[0]
                self.GSH3Queue.remove(first)
                gsh3inx = self.listWidget.row(first)
                scriptWidget = self.listWidget.takeItem(gsh3inx)
                if isinstance(scriptWidget, ScriptWidget):
                    self.GSH3pendingTest = scriptWidget
            if self.GSH3pendingTest:
                self.GSH3okToSend = False
                self.parent().acceptWidget(self.GSH3pendingTest)
                self.runTest.emit(self.GSH3pendingTest)
                self.GSH3pendingTest = None

            if self.GSH4okToSend and len(self.GSH4Queue) > 0:
                # NOTE: items removed from this list will NOT be removed from Qt automatically.
                first = self.GSH4Queue[0]
                self.GSH4Queue.remove(first)
                gsh4inx = self.listWidget.row(first)
                scriptWidget = self.listWidget.takeItem(gsh4inx)
                if isinstance(scriptWidget, ScriptWidget):
                    self.GSH4pendingTest = scriptWidget
            if self.GSH4pendingTest:
                self.GSH4okToSend = False
                self.parent().acceptWidget(self.GSH4pendingTest)
                self.runTest.emit(self.GSH4pendingTest)
                self.GSH4pendingTest = None

    def cancelTest(self):
        with self.qLock:
            selectedTests = self.listWidget.selectedItems()
            for singleTest in selectedTests:
                scriptWidget = self.listWidget.takeItem(self.listWidget.row(singleTest))

                if isinstance(scriptWidget, ScriptWidget):
                    scriptWidget.script.setCancelled()
                    scriptWidget.script.cancelScript()
                    self.parent().acceptWidget(scriptWidget)
                    self.unqueueTest.emit(scriptWidget)

    @qtc.pyqtSlot(ScriptWidget)
    def acceptTest(self, scriptWidget):
        with self.qLock:
            receivedWidget = self.parent().getWidget(scriptWidget)
            if receivedWidget:
                gsh = self.gshFromWidget(scriptWidget)
                if gsh == 1:
                    self.GSH1Queue.append(receivedWidget)
                elif gsh == 2:
                    self.GSH2Queue.append(receivedWidget)
                elif gsh == 3:
                    self.GSH3Queue.append(receivedWidget)
                elif gsh == 4:
                    self.GSH4Queue.append(receivedWidget)
                self.listWidget.addItem(receivedWidget)

    def gshFromWidget(self, scriptWidget):
        return scriptWidget.getGasHouse()

    @qtc.pyqtSlot(ScriptWidget)
    def ackTestEnded(self, scriptWidget):
        with self.qLock:
            gsh = self.gshFromWidget(scriptWidget)
            if gsh == 1:
                self.GSH1okToSend = True
                self.GSH1pendingTest = None
            elif gsh == 2:
                self.GSH2okToSend = True
                self.GSH2pendingTest = None
            elif gsh == 3:
                self.GSH3okToSend = True
                self.GSH3pendingTest = None
            elif gsh == 4:
                self.GSH4okToSend = True
                self.GSH4pendingTest = None


    def _addActionWidget(self):
        self.actionLayout = qtw.QVBoxLayout()
        self.actionLayout.setContentsMargins(0, 0, 0, 0)
        self.actionsWidget = qtw.QWidget()
        self.actionsWidget.setLayout(self.actionLayout)
        self.mainLayout.addWidget(self.actionsWidget)

        self.deleteButton = qtw.QToolButton()
        self.deleteIcon = self.deleteButton.style().standardIcon(qtw.QStyle.SP_DialogCancelButton)
        self.deleteButton.setIcon(self.deleteIcon)
        self.deleteButton.clicked.connect(self.cancelTest)
        self.actionLayout.addWidget(self.deleteButton)
        self.actionLayout.addStretch()

    def _addLayout(self):
        self.mainLayout = qtw.QHBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.mainLayout)

    def _addListWidget(self):
        self.listWidget = qtw.QListWidget()
        self.mainLayout.addWidget(self.listWidget)