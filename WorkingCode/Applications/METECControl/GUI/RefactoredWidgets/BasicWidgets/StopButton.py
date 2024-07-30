from PyQt5 import QtWidgets as qtw, QtCore

class StopButton(qtw.QPushButton):
    signalStop = QtCore.pyqtSignal([str], [list])

    def __init__(self, name, text=None, backgroundColor='red', textColor='white', emitStrings=None):
        qtw.QPushButton.__init__(self)
        if text == None:
            text = name
        self.setText(text)
        self.name = name

        self.setStyleSheet(f'background-color: {backgroundColor}; color: {textColor}')
        self.clicked.connect(lambda x: self.stop())
        self.setMaximumWidth(125)
        qtw.QSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)
        self.adjustSize()
        if emitStrings is None:
            emitStrings = []
        self.emitStrings = emitStrings

    def stop(self):
        for singleProcess in self.emitStrings:
            self.signalStop.emit(singleProcess)