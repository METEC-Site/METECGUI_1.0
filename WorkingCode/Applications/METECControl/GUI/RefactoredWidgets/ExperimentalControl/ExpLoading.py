import copy
import json
import pathlib

from Applications.METECControl.ExperimentDesigner.ExperimentDesigner import ExperimentDesigner
from Applications.METECControl.GUI.RefactoredWidgets.ExperimentalControl.ConfirmExperimentWidget import \
    ExperimentConfirmPopup
from Applications.METECControl.TestSuite.Deploying import Deploy
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw


class TestLoading(qtw.QGroupBox):
    queueSelectedTest = qtc.pyqtSignal(Deploy.ScriptWidget)

    def __init__(self, GUIInterface, name, title, parent, *args, **kwargs):
        qtw.QGroupBox.__init__(self, title, parent, *args)
        self.GUIInterface = GUIInterface
        self.name = name
        self.title = title
        self._addLayout()
        self._addListWidget()
        self._addActionWidget()

        self.errorMsg = qtw.QMessageBox()
        self.confirmer = ExperimentConfirmPopup(self.GUIInterface)

    def _addLayout(self):
        self.mainLayout = qtw.QHBoxLayout()
        self.mainLayout.setContentsMargins(0,0,0,0)
        self.setLayout(self.mainLayout)

    def _addListWidget(self):
        self.listWidget = qtw.QListWidget()
        self.mainLayout.addWidget(self.listWidget)

    def _addActionWidget(self):
        self.actionLayout = qtw.QVBoxLayout()
        self.actionLayout.setContentsMargins(0,0,0,0)
        self.actionsWidget = qtw.QWidget()
        self.actionsWidget.setLayout(self.actionLayout)
        self.mainLayout.addWidget(self.actionsWidget)

        self.runButton = qtw.QToolButton()
        self.runButton.setArrowType(qtc.Qt.RightArrow)
        self.runButton.clicked.connect(self.runTest)
        self.actionLayout.addWidget(self.runButton)

        self.deleteButton = qtw.QToolButton()
        self.deleteIcon = self.deleteButton.style().standardIcon(qtw.QStyle.SP_DialogCancelButton)
        self.deleteButton.setIcon(self.deleteIcon)
        self.editButton = qtw.QToolButton()
        editIcon = self.editButton.style().standardIcon(qtw.QStyle.SP_FileLinkIcon)
        self.editButton.setIcon(editIcon)
        self.editButton.clicked.connect(self.editTest)

        self.actionLayout.addWidget(self.deleteButton)
        self.actionLayout.addWidget(self.editButton)
        self.actionLayout.addStretch()

    # @qtc.pyqtSlot(str)
    def runTest(self):
        selectedFiles = self.listWidget.selectedItems()
        for itemWidget in selectedFiles:
            json = itemWidget.json
            confirmed, options = self.confirmTest(json=json) # todo: check why there are inconsistencies even though there shouldn't be?
            if confirmed:
                exp = copy.deepcopy(itemWidget.json)  # copy old experiment dictionary into new script
                exp['Experiment']['CloseAfterSection'] = options['CloseAfterSection']
                exp['Experiment']['CloseAfterIteration'] = options['CloseAfterIteration']
                exp['Experiment']['Iterations'] = options['Iterations']
                script = Deploy.TestScript(self.GUIInterface, exp)
                for gshNum in range(1, 5):
                    if gshNum in script.sources:
                        break
                newItem = Deploy.ScriptWidget(text=itemWidget.text(), parent=None, json=exp, script=script, fullPath=itemWidget.fullPath, gsh=gshNum)
                self.parent().acceptWidget(newItem)
                self.queueSelectedTest.emit(newItem)

    def editTest(self):
        selectedFiles = self.listWidget.selectedItems()
        for itemWidget in selectedFiles:
            ed = ExperimentDesigner(confirm=itemWidget.fullPath)
            newExperiment = ed.getConfirmedExperiment()
            if newExperiment:
                testScript = Deploy.TestScript(self.GUIInterface, newExperiment)
                itemWidget.script = testScript
                itemWidget.json = newExperiment

    def confirmTest(self, json):
        self.confirmer.initExperimentConfig(json)
        startable, experimentOptions = self.confirmer.exec()
        return startable, experimentOptions

    @qtc.pyqtSlot(str)
    def addFile(self, filename):
        with open(filename, 'r') as f:
            experiment = json.load(f)
        try:
            scriptName = pathlib.Path(filename).name
            listItem = Deploy.ScriptWidget(text=scriptName, parent=None, json=experiment, script=None, fullPath=filename)
            self.listWidget.addItem(listItem)
        except Exception as e:
            self.errorMsg.setText("Error loading experiment:\n"+str(e))
            self.errorMsg.exec()