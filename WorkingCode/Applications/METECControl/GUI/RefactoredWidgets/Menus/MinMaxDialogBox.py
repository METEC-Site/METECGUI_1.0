import PyQt5.QtWidgets as qtw
import Utils.Conversion as Conversion
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt

class MinMaxDialog(qtw.QDialog):
    minmaxchanged = QtCore.pyqtSignal(float, float, str)
    minmaxdefault = QtCore.pyqtSignal()

    def __init__(self, parent, displayUnit, inputUnit, displayMin, displayMax, absoluteMin=None, **kwargs):
        super().__init__()

        self.parent = parent
        self.inputUnit = inputUnit

        self.displayUnit = displayUnit

        self.absoluteMin = absoluteMin
        self.displayMin = displayMin
        self.displayMax = displayMax

        self.lineEditMin = qtw.QLineEdit()
        self.lineEditMax = qtw.QLineEdit()
        self.onlyDouble = QtGui.QDoubleValidator()
        self.lineEditMin.setValidator(self.onlyDouble)
        self.lineEditMax.setValidator(self.onlyDouble)

        self.lMin = qtw.QLabel()
        self.lMin.setText("Min")

        self.lMax = qtw.QLabel()
        self.lMax.setText("Max")

        self.setButton = qtw.QPushButton("Set")
        self.setButton.clicked.connect(self.setMinMaxButton)

        self.resetButton = qtw.QPushButton("Reset to Default")
        self.resetButton.clicked.connect(self.defaultMinMaxButton)

        self.layout = qtw.QGridLayout()
        self.layout.addWidget(self.lMax, 0, 0)
        self.layout.addWidget(self.lineEditMax, 0, 1)
        self.layout.addWidget(self.lMin, 1, 0)
        self.layout.addWidget(self.lineEditMin, 1, 1)
        self.layout.addWidget(self.setButton, 2, 0)
        self.layout.addWidget(self.resetButton, 2, 1)

        self.setLayout(self.layout)
        self.setWindowTitle("Set Max/Min Temp in "+self.displayUnit)
        self.setWindowModality(Qt.ApplicationModal)

    def showEvent(self, QShowEvent):
        self.displayMin, self.displayMax, self.displayUnit = self.parent.getDisplayInfo()
        self.setWindowTitle("Set Max/Min Temp in "+self.displayUnit)
        self.lineEditMin.setText(str(self.displayMin))
        self.lineEditMax.setText(str(self.displayMax))

    def setMinMaxButton(self):
        newmin = self.lineEditMin.text()
        newmax = self.lineEditMax.text()
        if len(newmin) == 0:
            newmin=0
        if len(newmax) == 0:
            newmax = 0
        try:
            newmax = float(newmax)
            newmin = float(newmin)
        except ValueError:
            errorbox = qtw.QMessageBox()
            errorbox.setText("Not all min/max values are numbers.")
            errorbox.exec_()
            return


        absoluteMin = Conversion.getAbsoluteMin(self.displayUnit)
        print("ABSOLUTEMIN: ",absoluteMin)
        displayText = f''
        if newmin == newmax:
            displayText = f"Max = {newmax} \nMin = {newmin} \nCannot have Max = Min"
        elif newmin > newmax:
            displayText = f"Max = {newmax} \nMin = {newmin} \nCannot have Max < Min"
        elif absoluteMin is not None and newmin < absoluteMin:
            displayText = f"Min = {newmin} \nMin must be > {absoluteMin}"
        if displayText:
            beb = qtw.QMessageBox()
            beb.setText(displayText)
            beb.exec_()
            return

        self.minmaxchanged.emit(newmin, newmax, self.displayUnit)
        self.close()

    def defaultMinMaxButton(self):
        self.close()
        self.minmaxdefault.emit()
