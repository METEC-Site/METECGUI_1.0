import logging

from Applications.METECControl.TestSuite.Deploying.Deploy import ScriptWidget, TestStates
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from Utils.QtUtils import CustomQTLock


class ExpRunning(qtw.QGroupBox):
    currentTest = qtc.pyqtSignal(dict, str)
    testStarted = qtc.pyqtSignal(ScriptWidget)
    unableToStart = qtc.pyqtSignal(ScriptWidget)
    testFinished = qtc.pyqtSignal(ScriptWidget)

    def __init__(self, GUIInterface, name, title, parent, *args, **kwargs):
        qtw.QGroupBox.__init__(self, title, parent, *args)
        self.GUIInterface = GUIInterface
        self.runLock = CustomQTLock()
        self.name = name
        self.GSH1CurrentTest = None
        self.GSH2CurrentTest = None
        self.GSH3CurrentTest = None
        self.GSH4CurrentTest = None
        self._addLayout()
        self._addListWidget()
        self._addActionWidget()

        self.updateTimer = qtc.QTimer()
        self.updateTimer.timeout.connect(self.checkTest)
        self.updateTimer.start(100)

    def isOkToStart(self, scriptWidget):
        with self.runLock:
            # todo: add a better check here, incorporating checks.
            gshSource = scriptWidget.getGasHouse()
            if gshSource == 1:
                if self.GSH1CurrentTest is None:
                    allUnUsed = True
                    if self.GUIInterface.checkGSHLock(gshSource) != (None, None):
                        allUnUsed = False
                    if allUnUsed:
                        for src in scriptWidget.script.sources:
                            self.GUIInterface.getGSHLock(src, "automated", str(scriptWidget.script.expID))
                    return allUnUsed
            elif gshSource == 2:
                if self.GSH2CurrentTest is None:
                    allUnUsed = True
                    if self.GUIInterface.checkGSHLock(gshSource) != (None, None):
                        allUnUsed = False
                    if allUnUsed:
                        for src in scriptWidget.script.sources:
                            self.GUIInterface.getGSHLock(src, "automated", str(scriptWidget.script.expID))
                    return allUnUsed
            elif gshSource == 3:
                if self.GSH3CurrentTest is None:
                    allUnUsed = True
                    if self.GUIInterface.checkGSHLock(gshSource) != (None, None):
                        allUnUsed = False
                    if allUnUsed:
                        for src in scriptWidget.script.sources:
                            self.GUIInterface.getGSHLock(src, "automated", str(scriptWidget.script.expID))
                    return allUnUsed
            elif gshSource == 4:
                if self.GSH4CurrentTest is None:
                    allUnUsed = True
                    if self.GUIInterface.checkGSHLock(gshSource) != (None, None):
                        allUnUsed = False
                    if allUnUsed:
                        for src in scriptWidget.script.sources:
                            self.GUIInterface.getGSHLock(src, "automated", str(scriptWidget.script.expID))
                    return allUnUsed

    def checkTest(self):
        with self.runLock:
            if not self.GSH1CurrentTest is None:
                if self.GSH1CurrentTest.script.getState() in [TestStates.unstarted, TestStates.queued]:
                    self.GSH1CurrentTest.script.start()
                    self.testStarted.emit(self.GSH1CurrentTest)

            if not self.GSH2CurrentTest is None:
                if self.GSH2CurrentTest.script.getState() in [TestStates.unstarted, TestStates.queued]:
                    self.GSH2CurrentTest.script.start()
                    self.testStarted.emit(self.GSH2CurrentTest)

            if not self.GSH3CurrentTest is None:
                if self.GSH3CurrentTest.script.getState() in [TestStates.unstarted, TestStates.queued]:
                    self.GSH3CurrentTest.script.start()
                    self.testStarted.emit(self.GSH3CurrentTest)

            if not self.GSH4CurrentTest is None:
                if self.GSH4CurrentTest.script.getState() in [TestStates.unstarted, TestStates.queued]:
                    self.GSH4CurrentTest.script.start()
                    self.testStarted.emit(self.GSH4CurrentTest)

    def cancelTestClicked(self):
        with self.runLock:
            selectedTests = self.listWidget.selectedItems()
            for singleTest in selectedTests:
                scriptWidget = self.listWidget.takeItem(self.listWidget.row(singleTest))

                if isinstance(scriptWidget, ScriptWidget):
                    if self.GSH1CurrentTest == scriptWidget:
                        thisTest = self.GSH1CurrentTest
                        thisTest.script.cancelScript()
                        try:
                            thisTest.script.finished.disconnect(self.completeGSH1Test)
                        except Exception as e:
                            pass
                    elif self.GSH2CurrentTest == scriptWidget:
                        thisTest = self.GSH2CurrentTest
                        thisTest.script.cancelScript()
                        try:
                            thisTest.script.finished.disconnect(self.completeGSH2Test)
                        except Exception as e:
                            pass
                    elif self.GSH3CurrentTest == scriptWidget:
                        thisTest = self.GSH3CurrentTest
                        thisTest.script.cancelScript()
                        try:
                            thisTest.script.finished.disconnect(self.completeGSH3Test)
                        except Exception as e:
                            pass
                    elif self.GSH4CurrentTest == scriptWidget:
                        thisTest = self.GSH4CurrentTest
                        thisTest.script.cancelScript()
                        try:
                            thisTest.script.finished.disconnect(self.completeGSH4Test)
                        except Exception as e:
                            pass
                    self.parent().acceptWidget(scriptWidget)

    def handleCancelTest(self):
        with self.runLock:
            pass
            # if not self.GSH1CurrentTest is None:
            #     self.completeGSH1Test()
            #
            # if not self.GSH2CurrentTest is None:
            #     self.completeGSH2Test()
            #
            # if not self.GSH3CurrentTest is None:
            #     self.completeGSH3Test()
            #
            # if not self.GSH4CurrentTest is None:
            #     self.completeGSH4Test()

    @qtc.pyqtSlot(ScriptWidget)
    def acceptTest(self, scriptWidget):
        with self.runLock:
            sWidget = self.parent().getWidget(scriptWidget)
            if self.isOkToStart(sWidget):
                src = sWidget.getGasHouse()
                self.listWidget.addItem(sWidget)
                if src == 1:
                    sWidget.script.finished.connect(self.completeGSH1Test)
                    self.GSH1CurrentTest = scriptWidget
                elif src == 2:
                    sWidget.script.finished.connect(self.completeGSH2Test)
                    self.GSH2CurrentTest = scriptWidget
                elif src == 3:
                    sWidget.script.finished.connect(self.completeGSH3Test)
                    self.GSH3CurrentTest = scriptWidget
                elif src == 4:
                    sWidget.script.finished.connect(self.completeGSH4Test)
                    self.GSH4CurrentTest = scriptWidget
                sWidget.script.cancelled.connect(self.handleCancelTest)
            else:
                self.parent().acceptWidget(scriptWidget)
                self.unableToStart.emit(scriptWidget)

    def completeGSH1Test(self):
        with self.runLock:
            scriptWidget = self.GSH1CurrentTest
            self.GSH1CurrentTest = None
            self.disconnectGSH1Signals()
            self.listWidget.takeItem(self.listWidget.row(scriptWidget))
            self.parent().acceptWidget(scriptWidget)
            self.testFinished.emit(scriptWidget)
            for src in scriptWidget.script.sources:
                self.GUIInterface.releaseGSHLock(src, "automated", str(scriptWidget.script.expID))
            logging.info(f'Ending Test {scriptWidget.text()}')

    def disconnectGSH1Signals(self):
        with self.runLock:
            try:
                self.GSH1CurrentTest.script.finished.disconnect(self.completeGSH1Test)
            except:
                pass
            try:
                self.GSH1CurrentTest.script.cancelled.disconnect(self.cancelTestClicked)
            except:
                pass

    def completeGSH2Test(self):
        with self.runLock:
            scriptWidget = self.GSH2CurrentTest
            self.GSH2CurrentTest = None
            self.disconnectGSH2Signals()
            self.listWidget.takeItem(self.listWidget.row(scriptWidget))
            self.parent().acceptWidget(scriptWidget)
            self.testFinished.emit(scriptWidget)
            for src in scriptWidget.script.sources:
                self.GUIInterface.releaseGSHLock(src, "automated", str(scriptWidget.script.expID))
            logging.info(f'Ending Test {scriptWidget.text()}')

    def disconnectGSH2Signals(self):
        with self.runLock:
            try:
                self.GSH2CurrentTest.script.finished.disconnect(self.completeGSH2Test)
            except:
                pass
            try:
                self.GSH2CurrentTest.script.cancelled.disconnect(self.cancelTestClicked)
            except:
                pass

    def completeGSH3Test(self):
        with self.runLock:
            scriptWidget = self.GSH3CurrentTest
            self.GSH3CurrentTest = None
            self.disconnectGSH3Signals()
            self.listWidget.takeItem(self.listWidget.row(scriptWidget))
            self.parent().acceptWidget(scriptWidget)
            self.testFinished.emit(scriptWidget)
            for src in scriptWidget.script.sources:
                self.GUIInterface.releaseGSHLock(src, "automated", str(scriptWidget.script.expID))
            logging.info(f'Ending Test {scriptWidget.text()}')

    def disconnectGSH3Signals(self):
        with self.runLock:
            try:
                self.GSH3CurrentTest.script.finished.disconnect(self.completeGSH3Test)
            except:
                pass
            try:
                self.GSH3CurrentTest.script.cancelled.disconnect(self.cancelTestClicked)
            except:
                pass

    def completeGSH4Test(self):
        with self.runLock:
            scriptWidget = self.GSH4CurrentTest
            self.GSH4CurrentTest = None
            self.disconnectGSH4Signals()
            self.listWidget.takeItem(self.listWidget.row(scriptWidget))
            self.parent().acceptWidget(scriptWidget)
            self.testFinished.emit(scriptWidget)
            for src in scriptWidget.script.sources:
                self.GUIInterface.releaseGSHLock(src, "automated", str(scriptWidget.script.expID))
            logging.info(f'Ending Test {scriptWidget.text()}')

    def disconnectGSH4Signals(self):
        with self.runLock:
            try:
                self.GSH4CurrentTest.script.finished.disconnect(self.completeGSH4Test)
            except:
                pass
            try:
                self.GSH4CurrentTest.script.cancelled.disconnect(self.cancelTestClicked)
            except:
                pass


    @qtc.pyqtSlot(str, str, int)
    def acceptValveCommand(self, source, valveName, value):
        """ Accepts a command from a running test.

        Command should be a dictionary of valve names and values (0 for open, 1 for close)

        :param command:
        :return:
        """
        if value == 1:
            self.GUIInterface.closeValve(source, args=[valveName])
        else:
            self.GUIInterface.openValve(source, args=[valveName])

    def _addLayout(self):
        self.mainLayout = qtw.QHBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.mainLayout)

    def _addListWidget(self):
        self.listWidget = qtw.QListWidget()
        self.mainLayout.addWidget(self.listWidget)

    def _addActionWidget(self):
        self.actionLayout = qtw.QVBoxLayout()
        self.actionLayout.setContentsMargins(0, 0, 0, 0)
        self.actionsWidget = qtw.QWidget()
        self.actionsWidget.setLayout(self.actionLayout)
        self.mainLayout.addWidget(self.actionsWidget)

        self.deleteButton = qtw.QToolButton()
        self.deleteIcon = self.deleteButton.style().standardIcon(qtw.QStyle.SP_DialogCancelButton)
        self.deleteButton.setIcon(self.deleteIcon)
        self.deleteButton.clicked.connect(self.cancelTestClicked)
        self.actionLayout.addWidget(self.deleteButton)
        self.actionLayout.addStretch()