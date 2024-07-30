
import PyQt5.QtWidgets as qtw
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.StopButton import StopButton
from Framework.BaseClasses.QtMixin import QtMixin
from PyQt5.QtGui import QPainter, QBrush

"""
.. _control-panel-module:

#################
Control Panel
#################

:Authors: Aidan Duggan, Jerry Duggan
:Date: April 30, 2019

This module provides the Control Panel Widget.
"""
__docformat__ = 'reStructuredText'

class ControlPanel(qtw.QFrame, QtMixin):

    def __init__(self, GUIInterface,
                 name=None, parent=None, readerName=None,
                 *args, **kwargs):
        QtMixin.__init__(self, GUIInterface=GUIInterface, name=name, parent=parent, *args, **kwargs)
        qtw.QFrame.__init__(self, parent=parent)
        self.layout = qtw.QGridLayout()
        self.painter = QPainter()
        self.brush = QBrush()

        self.stopButton = StopButton('Close Valves', emitStrings=[readerName])
        self.stopButton.signalStop.connect(self.GUIInterface.shutdownDevice)

        self.layout.addWidget(self.stopButton, 0, 0)
        self.setLayout(self.layout)
        self.update()
        self.setFrameShape(qtw.QFrame.WinPanel)
        self.setFrameShadow(qtw.QFrame.Sunken)
        self.maxHeight = self.stopButton.height() + 5
        self.setMaximumHeight(self.maxHeight)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(qtw.QSizePolicy(qtw.QSizePolicy.Minimum, qtw.QSizePolicy.Minimum))
        self.adjustSize()

    def update(self):
        qtw.QFrame.update(self)
        self.stopButton.update()

    def paintEvent(self, event):
        pass
        # self.painter.begin(self)
        # self.painter.fillRect(self.frameRect(), self.brush)
        # self.painter.end()