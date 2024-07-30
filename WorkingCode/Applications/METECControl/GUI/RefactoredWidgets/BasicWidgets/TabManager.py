import PyQt5.QtWidgets as qtw
from Framework.BaseClasses.QtMixin import QtMixin

class TabManager(qtw.QTabWidget, QtMixin):
    def __init__(self, GUIInterface,
                 name=None, parent=None,
                 *args, **kwargs):
        QtMixin.__init__(self, GUIInterface, name=name, parent=parent, *args, **kwargs)
        qtw.QTabWidget.__init__(self, parent=parent)
        self.layout = qtw.QGridLayout()
        self.setLayout(self.layout)

    def update(self):
        qtw.QTabWidget.update(self)