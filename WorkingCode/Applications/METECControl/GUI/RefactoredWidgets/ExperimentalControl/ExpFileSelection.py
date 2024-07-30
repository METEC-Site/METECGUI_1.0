import json
import os

from Framework.BaseClasses.QtMixin import QtMixin
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from Utils.ExperimentUtils import verifyExperiment


class FileExtError(Exception): pass

class ExpFileSelection(qtw.QWidget, QtMixin):
    fileSelected = qtc.pyqtSignal(str)

    def __init__(self, GUIInterface, name, parent, defaultSearchDir = None, *args, **kwargs):
        qtw.QWidget.__init__(self, *args)
        QtMixin.__init__(self, GUIInterface=GUIInterface, name=name, parent=parent, *args, **kwargs)

        if type(defaultSearchDir) is str and os.path.exists(defaultSearchDir):
            self.defaultSerachDir = defaultSearchDir
        else:
            self.defaultSerachDir = os.path.dirname(__file__)

        self.fileDialog = qtw.QFileDialog()
        self._addLayout()
        self._addButton()
        self._addTextbox()
        self._addSelectFileButton()
        self._addErrorPopupWindow()

    def _addLayout(self):
        self.lout = qtw.QHBoxLayout()
        self.lout.setContentsMargins(0,0,0,0)
        self.setLayout(self.lout)

    def _addButton(self):
        self.button = qtw.QPushButton(self)
        self.button.setText('Select File')
        self.lout.addWidget(self.button)
        # self.button.show()
        # self.buttonSpacer = qtw.QSpacerItem()
        # self.lout.addSpacerItem(self.buttonSpacer)
        self.button.clicked.connect(self.selectFile)

    def _addTextbox(self):
        self.textBox = qtw.QTextEdit()
        self.textBox.setFixedHeight(self.button.height())
        # self.textBox.setSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum)
        self.lout.addWidget(self.textBox)

    def _addSelectFileButton(self):
        self.selectFileLabel = qtw.QLabel('Add File: ')
        self.lout.addWidget(self.selectFileLabel)
        self.selectFileButton = qtw.QToolButton()
        self.selectFileButton.setArrowType(qtc.Qt.RightArrow)
        self.lout.addWidget(self.selectFileButton)
        self.selectFileButton.clicked.connect(self.emitFile)
        self.lout.addStretch()

    def _addErrorPopupWindow(self):
        self.errorDialog = qtw.QErrorMessage()
        # self.popup = qtw.QWidget()
        # self.popupLayout = qtw.QVBoxLayout()
        # self.popup.setLayout(self.popupLayout)
        # self.popupMessage = qtw.QLabel('Could not add file due to error:')
        # self.popupError = qtw.QLabel(f'')
        # self.popupButton = qtw.QPushButton('OK')
        # self.popupButton.clicked.connect(self.hidePopup)
        # self.popupLayout.addWidget(self.popupMessage)
        # self.popupLayout.addWidget(self.popupError)
        # self.popupLayout.addWidget(self.popupButton)
        # self.popup.hide()

    def selectFile(self):
        filename = self.fileDialog.getOpenFileName(self, 'Select Experiment File')
        if filename:
            if filename[0]:
                self.textBox.setText(filename[0])

    @qtc.pyqtSlot()
    def emitFile(self):
        try:
            verified = self.checkFile(self.textBox.toPlainText())
            if verified:
                self.fileSelected.emit(self.textBox.toPlainText())
                self.textBox.setText('')
            else:
                # self.popupError.setText('Json file is not a properly formatted script.')
                self.errorDialog.showMessage('Json file is not a properly formatted script.')
                # self.popup.show()
        except FileExistsError:
            # self.popupError.setText('File does not exist!')
            self.errorDialog.showMessage('File does not exist!')
            # self.popup.show()
        except FileExtError:
            # self.popupError.setText('File extension should be .json')
            self.errorDialog.showMessage('File extension should be .json')
            # self.popup.show()
        except Exception as e:
            self.errorDialog.showMessage(f'Error loading the json script: {e}')
            # self.popupError.setText(f'Error loading the json script: {e}')
            # self.popup.show()

    # @qtc.pyqtSlot()
    # def hidePopup(self):
        # self.popup.hide()
        # self.popupError.setText('')
        # self.textBox.setText('')

    def checkFile(self, filename):
        if not os.path.exists(filename):
            raise FileExistsError
        if not os.path.splitext(filename)[1] == '.json':
            raise FileExtError
        with open(filename) as jsonFile:
            experiment = json.load(jsonFile)
            verified = verifyExperiment(experiment)
        return verified