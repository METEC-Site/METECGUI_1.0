from abc import ABC, abstractmethod
from threading import RLock, Event

TermLock = RLock()
StopperEvent = {'stopper': None}

class Initiator(ABC):
    def __init__(self, **kwargs):
        self.started = False

    @abstractmethod
    def start(self):
        raise NotImplementedError

class Terminator(ABC):
    def __init__(self, **kwargs):
        pass

    def isTimeToStop(self):
        if self.getStopper().is_set():
            return True
        return False

    def getStopper(self):
        with TermLock:
            if StopperEvent['stopper'] is None:
                StopperEvent['stopper'] = Event()
            return StopperEvent['stopper']

    @abstractmethod
    def end(self):
        raise NotImplementedError