from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc

from Framework.BaseClasses.QtMixin import QtMixin
from Utils.QtUtils import CustomQTLock
from Applications.METECControl.GUI.RefactoredWidgets.ExperimentalControl.ExpFileSelection import ExpFileSelection
from Applications.METECControl.GUI.RefactoredWidgets.ExperimentalControl.ExpLoading import TestLoading
from Applications.METECControl.GUI.RefactoredWidgets.ExperimentalControl.ExpRunning import ExpRunning
from Applications.METECControl.GUI.RefactoredWidgets.ExperimentalControl.ExpCompletion import ExpCompletion
from Applications.METECControl.GUI.RefactoredWidgets.ExperimentalControl.ExpQueue import ExpQueue

class ExpContainer(qtw.QWidget, QtMixin):
    def __init__(self, GUIInterface, name, parent, *args, **kwargs):
        QtMixin.__init__(self, GUIInterface, name=name, parent=parent, *args, **kwargs)
        self.GUIInterface = GUIInterface
        self.contLock = CustomQTLock()
        self.name = name
        qtw.QWidget.__init__(self, parent)
        self._setupLayout()
        self._addFileSelect()
        self._addLoading()
        self._addQueues()
        self._addRunning()
        self._addCompleted()
        self._connectButtons()
        self._addSpacer()

    def _setupLayout(self):
        self.lout = qtw.QVBoxLayout()
        self.setLayout(self.lout)
        self.lout.setContentsMargins(0, 0, 0, 0)

    def _addFileSelect(self):
        self.fileSelectWidget = ExpFileSelection(self.GUIInterface, 'AddFileButton', self)
        self.lout.addWidget(self.fileSelectWidget)

    def _addLoading(self):
        self.loadingWidget = TestLoading(self.GUIInterface, 'loadingWidget', 'Loaded Tests', self)
        self.lout.addWidget(self.loadingWidget)

    def _addQueues(self):
        self.queueWidget = ExpQueue(self.GUIInterface, 'queueWidget', 'Queued Tests', self)
        self.queueWidget.deleteButton.clicked.connect(self.cancelSelectedFromQueue)
        self.lout.addWidget(self.queueWidget)

    def _addRunning(self):
        self.runningWidget = ExpRunning(self.GUIInterface, 'runningWidget', "Running Tests", self)
        self.lout.addWidget(self.runningWidget)

    def _addCompleted(self):
        self.completedWidget = ExpCompletion(self.GUIInterface, 'completedWidget', 'Finished Tests', self)
        self.lout.addWidget(self.completedWidget)

    @qtc.pyqtSlot()
    def cancelSelectedFromQueue(self):
        removeExpIDs = self.queueWidget.getSelectedIDs()
        self.queueWidget.removeSelected()
        for expID in removeExpIDs:
            self.cancelExperiment(expID)

    def cancelExperiment(self, expID):
        pass

    def _connectButtons(self):
        self.fileSelectWidget.fileSelected.connect(self.loadingWidget.addFile)
        self.loadingWidget.queueSelectedTest.connect(self.queueWidget.acceptTest)
        self.queueWidget.runTest.connect(self.runningWidget.acceptTest)
        self.queueWidget.unqueueTest.connect(self.completedWidget.acceptTest)
        self.runningWidget.testFinished.connect(self.queueWidget.ackTestEnded)
        self.runningWidget.testFinished.connect(self.completedWidget.acceptTest)

    def getWidget(self, widget):
        with self.contLock:
            if widget in self.heldWidgets:
                self.heldWidgets.remove(widget)
                return widget

    def acceptWidget(self, widget):
        with self.contLock:
            if not widget in self.heldWidgets:
                self.heldWidgets.append(widget)

    def _addSpacer(self):
        self.lout.addStretch()