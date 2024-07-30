from abc import ABC, ABCMeta, abstractmethod

import PyQt5.QtCore as qtc


# class nonConflictMeta(type(qtw.QWidget), ABCMeta): pass
#
# class QtWrapper(qtw.QWidget, ABC, metaclass=nonConflictMeta):
class NonConflictMeta(type(qtc.QObject), ABCMeta):
    pass

class QtMixin(qtc.QObject):
    def __init__(self, GUIInterface=None,
                 name=None, label=None, parent=None, updateInterval=10,
                 *args, **kwargs):

        # qtw.QWidget.__init__(self, self.parentObj)
        qtc.QObject.__init__(self,parent)
        self.parent = parent

        if name==None:
            raise NameError(f"A name must be supplied to the widget {self}")
        self.name = name
        self.label = label if label else self.name
        self.GUIInterface = GUIInterface
        self.updateTimer = qtc.QTimer()
        self.updateTimer.timeout.connect(self.update)
        self.updateTimer.setSingleShot(False)
        self.updateInterval = updateInterval
        self.updateTimer.start(updateInterval)


class DataWidget(ABC, QtMixin, metaclass=NonConflictMeta):

    @abstractmethod
    def setRawValue(self, rawFieldname=None, rawValue=None):
        raise NotImplementedError

    @abstractmethod
    def setCorrValue(self, corrFieldname=None, corrValue=None):
        raise NotImplementedError

class ReceiverWidget(ABC, QtMixin, metaclass=NonConflictMeta):
    def __init__(self, commandStreams=None, eventStreams=None, rawDataStreams=None, corrDataStreams=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addStreams(commandStreams)
        self.addStreams(rawDataStreams)
        self.addStreams(corrDataStreams)
        self.addStreams(eventStreams)

    def addStreams(self, streams):
        if not streams is None:
            for stream in streams:
                if not stream is None:
                    sourceName = stream['source']
                    channelType = stream['channelType']
                    self.GUIInterface.subscribeWidget(self, sourceName, channelType)

    def addStream(self, stream):
        if not stream is None:
            sourceName = stream['source']
            channelType = stream['channelType']
            self.GUIInterface.subscribeWidget(self, sourceName, channelType)