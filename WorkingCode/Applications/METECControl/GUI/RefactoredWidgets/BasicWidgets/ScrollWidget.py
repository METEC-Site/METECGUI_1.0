from Framework.BaseClasses.QtMixin import QtMixin
from PyQt5 import QtWidgets as qtw


class ScrollWidget(qtw.QWidget, QtMixin):
    def __init__(self, GUIInterface,
                 name=None, parent=None,
                 *args, **kwargs):
        QtMixin.__init__(self, GUIInterface, name, parent, *args, **kwargs)
        qtw.QWidget.__init__(self, parent)
        self.scrollArea = qtw.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.bw = qtw.QWidget(self)
        self.bwLout = qtw.QHBoxLayout()
        self.bw.setLayout(self.bwLout)
        self.lout = qtw.QHBoxLayout()
        self.setLayout(self.lout)
        self.scrollArea.setWidget(self.bw)
        self.lout.addWidget(self.scrollArea)
        self.bw.wheelEvent = self.wheelEvent

    def update(self):
        qtw.QScrollArea.update(self.scrollArea)
        self.bw.update()

    def addWidget(self, widget, *args, **kwargs):
        self.bwLout.addWidget(widget, *args, **kwargs)