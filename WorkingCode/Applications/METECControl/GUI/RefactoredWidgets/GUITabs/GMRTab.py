from Applications.METECControl.GUI.RefactoredWidgets.Controllers.GMR import
from Framework.BaseClasses.QtMixin import QtMixin
from PyQt5 import QtWidgets as qtw


class GMR(qtw.QWidget, QtMixin):

    def __init__(self, GUIInterface, name=None, parent=None):
        QtMixin.__init__(self, GUIInterface, name=name, parent=parent)
        qtw.QWidget.__init__(self, parent=parent)
        self.layout = qtw.QGridLayout()
        self.setLayout(self.layout)
        self.buildGUI()

    def buildGUI(self):
        self.ethaneControl =

    def update(self):
        qtw.QWidget.update(self)