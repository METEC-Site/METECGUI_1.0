import PyQt5.QtWidgets as qtw
from Framework.BaseClasses.QtMixin import DataWidget


class SensorPropertiesMenu(qtw.QMenu, DataWidget):
    def __init__(self, GUIInterface, name=None, parent=None, label=None, sensorproperties=None):
        DataWidget.__init__(self, GUIInterface=GUIInterface, name=name, label=label, parent=parent)
        qtw.QMenu.__init__(self, "Sensor Properties")
        self.mainWidget = qtw.QWidget()
        self.layout = qtw.QGridLayout()
        self.mainWidget.setLayout(self.layout)
        self.numRows = 0
        self.dataWidgets = {}
        self.addData(sensorproperties)

        self.widgetAction = qtw.QWidgetAction(self)
        self.widgetAction.setDefaultWidget(self.mainWidget)
        self.addAction(self.widgetAction)

    def setRawValue(self, rawFieldname=None, rawValue=None):
        raise NotImplementedError

    def setCorrValue(self, corrFieldname=None, corrValue=None):
        raise NotImplementedError

    def addData(self, dataDictionary):
        for key, val in dataDictionary.items():
            self.numRows+=1
            label1 = qtw.QLabel(f"{key}: ")
            val = str(val)
            if len(val) > 0:
                label2 = qtw.QLabel(val)
                label2.setStyleSheet("color: blue")
                self.layout.addWidget(label1, self.numRows, 0)
                self.layout.addWidget(label2, self.numRows, 1)
                self.dataWidgets[key] = (label1, label2)

    def updateData(self, data):
        for key, value in data.items():
            label = self.dataWidgets.get(key)
            if label:
                label[1].setText(str(value))