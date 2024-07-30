from Applications.METECControl.ExperimentDesigner.DesignerConfigs import EmissionCategories, getEmissionCategory
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw


class PresetAction(qtc.QObject):
    createAction = qtc.pyqtSignal(str, int, int, EmissionCategories, str) #ep, timing, flowlevel, category, note
    finishedAdding = qtc.pyqtSignal()

    def __init__(self):
        qtc.QObject.__init__(self)
        self.setupWidget = qtw.QWidget()
        # self.enterEP = qtw.QLineEdit()
        # self.epSelector = EmissionPointSelector()
        self.selectedEP = None
        self.categoryBox = qtw.QComboBox()
        categories = list(map(lambda x: x.value, EmissionCategories))
        self.categoryBox.addItems(categories)
        self.addButton = qtw.QPushButton(text="Add")
        self.addButton.clicked.connect(lambda x: self.emitActions())

    def getSetupWidget(self):
        return self.setupWidget

    def setEPConfig(self, epConfig):
        pass
        # self.epSelector.setEPConfig(epConfig)

    def setSelectedEP(self, ep):
        self.selectedEP = ep
        # self.epSelector.setSelectedEP(ep)

    def emitActions(self):
        pass


class StairPreset(PresetAction):

    def __init__(self):
        PresetAction.__init__(self)
        self.startTimeWidget = qtw.QSpinBox()
        self.startTimeWidget.setRange(-999999999, 999999999)
        self.stepDurationWidget = qtw.QSpinBox()
        self.stepDurationWidget.setRange(1, 999999999)
        self.numberOfStepsWidget = qtw.QSpinBox()
        self.numberOfStepsWidget.setRange(1, 999999999)
        # setup layout
        layout = qtw.QGridLayout()
        self.setupWidget.setLayout(layout)
        # layout.addWidget(qtw.QLabel(text="Select Emission Point"), 0, 1, 1, 2)
        # layout.addWidget(self.epSelector, 1, 1, 1, 2)
        layout.addWidget(qtw.QLabel(text="Start Time"), 2, 1)
        layout.addWidget(self.startTimeWidget, 2, 2)
        layout.addWidget(qtw.QLabel(text="Step Duration"), 3, 1)
        layout.addWidget(self.stepDurationWidget, 3, 2)
        layout.addWidget(qtw.QLabel(text="Number Steps"), 4, 1)
        layout.addWidget(self.numberOfStepsWidget, 4, 2)
        layout.addWidget(self.categoryBox, 5, 1, 1, 2)
        layout.addWidget(self.addButton, 6, 1)

    def emitActions(self):
        startTime = self.startTimeWidget.value()
        stepDir = self.stepDurationWidget.value()
        numsteps = self.numberOfStepsWidget.value()
        for i in range(numsteps):
            # self.createAction.emit(self.epSelector.getCurrentEP(), startTime+i*stepDir, (i+1)%16, "Stairs Preset")
            self.createAction.emit(self.selectedEP, startTime+i*stepDir, (i+1)%16, getEmissionCategory(self.categoryBox.currentText()), "Stairs Preset")
        self.finishedAdding.emit()


class IntermittentPreset(PresetAction):

    def __init__(self):
        PresetAction.__init__(self)
        self.startTimeWidget = qtw.QSpinBox()
        self.startTimeWidget.setRange(0,999999999)
        self.level1Widget = qtw.QSpinBox()
        self.level1Widget.setRange(0,15)
        self.duration1Widget = qtw.QSpinBox()
        self.duration1Widget.setRange(1, 999999999)
        self.level2Widget = qtw.QSpinBox()
        self.level2Widget.setRange(0,15)
        self.duration2Widget = qtw.QSpinBox()
        self.duration2Widget.setRange(1, 999999999)
        self.iterationsWidget = qtw.QSpinBox()
        self.iterationsWidget.setRange(1, 999999999)

        layout = qtw.QGridLayout()
        self.setupWidget.setLayout(layout)
        layout.addWidget(qtw.QLabel(text="Start Time"), 1, 1)
        layout.addWidget(self.startTimeWidget, 1, 2)
        layout.addWidget(qtw.QLabel(text="Level 1"), 2, 1)
        layout.addWidget(self.level1Widget, 2, 2)
        layout.addWidget(qtw.QLabel(text="Duration 1"), 3, 1)
        layout.addWidget(self.duration1Widget, 3, 2)
        layout.addWidget(qtw.QLabel(text="Level 2"), 4, 1)
        layout.addWidget(self.level2Widget, 4, 2)
        layout.addWidget(qtw.QLabel(text="Duration 2"), 5, 1)
        layout.addWidget(self.duration2Widget, 5, 2)
        layout.addWidget(qtw.QLabel(text="Iterations"), 6, 1)
        layout.addWidget(self.iterationsWidget, 6, 2)
        layout.addWidget(self.categoryBox, 7, 1, 1, 2)
        layout.addWidget(self.addButton, 8, 1)

    def emitActions(self):
        dur1 = self.duration1Widget.value()
        dur2 = self.duration2Widget.value()
        level1 = self.level1Widget.value()
        level2 = self.level2Widget.value()
        category = getEmissionCategory(self.categoryBox.currentText())
        time = self.startTimeWidget.value()
        for i in range(self.iterationsWidget.value()):
            self.createAction.emit(self.selectedEP, time, level1, category, "Intermittent Preset")
            time += dur1
            self.createAction.emit(self.selectedEP, time, level2, category, "Intermittent Preset")
            time += dur2
        self.finishedAdding.emit()
