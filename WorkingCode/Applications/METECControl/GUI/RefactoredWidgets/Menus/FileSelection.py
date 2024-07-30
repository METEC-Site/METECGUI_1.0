from Framework.BaseClasses.QtMixin import QtMixin
from PyQt5 import QtWidgets
from Utils.QtUtils import getApp



class FileDialog(QtWidgets.QFileDialog, QtMixin):
    def __init__(self, GUIInterface,
                 name=None, parent=None,
                 *args, **kwargs):
        self.app = getApp()
        QtMixin.__init__(self, GUIInterface, name=name, parent=parent, *args, **kwargs)
        QtWidgets.QFileDialog.__init__(self, parent)
        self.title = self.label
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.geo = [self.left, self.top, self.width, self.height]
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(*self.geo)
        self.hide()

    def openFileNamesDialog(self):
        options = self.Options()
        options |= self.DontUseNativeDialog
        fileName, _ = self.getOpenFileNames(self, 'Choose A File', '', 'All Files (*)', options=options)
        if fileName:
            return fileName

    def openDirNamesDialog(self, initialLocation = ''):
        options = self.Options()
        options |= self.DontUseNativeDialog
        dirName = self.getExistingDirectory(self, 'Choose A Directory', initialLocation, options=options)
        if dirName:
            return dirName

    def saveFileDialog(self):
        options = self.Options()
        options |= self.DontUseNativeDialog
        fileName, _ = self.getSaveFileName(self, "Save File As", "All Files (*)", options=options)
        if fileName:
            return fileName