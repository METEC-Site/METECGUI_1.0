from PyQt5 import QtWidgets as qtw

from Utils import TimeUtils as tu


class AdhocController(qtw.QWidget):


    def __init__(self, GUIInterface, gasHouse=1, controllerName="GSH-X"):
        qtw.QWidget.__init__(self)
        self.guiInterface = GUIInterface
        label_experimentNumber = qtw.QLabel("Experiment ID:")
        label_experimentNumber.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)
        self.idDisplay = qtw.QLabel(text='-')
        self.idDisplay.setMinimumWidth(25)
        self.idDisplay.setMaximumHeight(30)
        self.idDisplay.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)
        self.idDisplay.setFrameShape(qtw.QFrame.Panel)
        self.noteDisplay = qtw.QTextEdit()
        self.noteDisplay.setPlaceholderText("insert notes: NO COMMAS OR TABS")
        self.controllerName = controllerName
        self.gasHouse=gasHouse
        button_start = qtw.QPushButton(text="Start")
        button_start.clicked.connect(self.start)
        button_stop = qtw.QPushButton(text="Stop")
        button_stop.clicked.connect(self.stop)

        layout = qtw.QGridLayout()
        layout.addWidget(label_experimentNumber, 0, 0)
        layout.addWidget(self.idDisplay, 1, 0, 1, 2)
        layout.addWidget(self.noteDisplay, 3,0,2,2)
        layout.addWidget(button_start, 2,0)
        layout.addWidget(button_stop, 2,1)
        self.setLayout(layout)

    def setExperimentID(self, txt):
        self.idDisplay.setText(txt)

    def getExperimentID(self):
        return self.idDisplay.text()

    def start(self):
        experimentID = f'{self.controllerName}EXP{tu.nowDT().strftime("%y%m%d%H%M%S")}' # add experiment number
        currentName, currentExp = self.guiInterface.getGSHLock(self.gasHouse, self.controllerName, experimentID)
        if (currentName, currentExp) == (None, None):
            self.setExperimentID(experimentID)
            self.guiInterface.emitExpStart(experimentID, self.gasHouse, None, timestamp=tu.nowEpoch())
        experimentID = f'{self.controllerName}EXP{tu.nowDT().strftime("%y%m%d%H%M%S")}'  # add experiment number
        self.setExperimentID(experimentID)

    def stop(self):
        if self.guiInterface.checkGSHLock(self.gasHouse) == (self.controllerName, self.idDisplay.text()):
            self.guiInterface.releaseGSHLock(self.gasHouse, self.controllerName, self.getExperimentID())
            self.guiInterface.emitExpEnd(self.idDisplay.text(), self.gasHouse, note=self.getNote())
            self.setExperimentID("-")
            self.noteDisplay.clear()

    def getNote(self):
        txt = self.noteDisplay.toPlainText()
        txt = txt.replace(',', '')
        txt = txt.replace('\t', '')
        return txt

    # def changeCurrentExperiment(self, expID, gasHouse, eventType):
    #     if gasHouse == self.gasHouse:
    #         if eventType == EventTypes.ExperimentStart or eventType == EventTypes.CalStart:
    #             self.setExperimentID(expID)
    #         else:
    #             self.setExperimentID('-')
    #             self.noteDisplay.clear()

if __name__ == '__main__':
    import sys
    app = qtw.QApplication(sys.argv)
    a = AdhocController()
    a.show()
    app.exec()