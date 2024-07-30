import time
from abc import ABC, abstractmethod
from queue import Queue
from threading import Thread, RLock

from Framework.BaseClasses.LoggingObject import LoggingObject
from Framework.BaseClasses.NamedObject import NamedObject
from Framework.BaseClasses.Sentinel import Sentinel
from Framework.BaseClasses.StartStop import Initiator, Terminator
from Utils import ClassUtils as cu
from Utils import Exceptions as ex


class Destination(NamedObject, ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def handlePackage(self, package):
        raise NotImplementedError

    def _accept(self, package):
        self.handlePackage(package)

    def accept(self, package):
        if not cu.isPackage(package):
            raise ex.InstanceError(f'Object {package} passed to accept of {self.getName()} does not inherit from Package.')
        return self._accept(package)


class QueuedDestination(Destination):
    def __init__(self, inputQueue=None, **kwargs):
        super().__init__(**kwargs)
        self.inputQueue=None
        self.setInputQueue(inputQueue)

    def setInputQueue(self, inputQueue=None, overwrite=False):
        if self.inputQueue is None or overwrite or inputQueue is self.inputQueue:
            self.inputQueue = inputQueue if isinstance(inputQueue, Queue) is None else Queue()
        else:
            raise ex.ResourceAllocationError(f'Cannot allocate new input queue to {self.getName()} as one already exists and overwrite is set to False.')

    def _accept(self, package):
        # note that this Queued destination needs a way to get things off of the queue and call "handleIncomingPackage" on them.
        self.inputQueue.put(package)

class ThreadedDestination(QueuedDestination, LoggingObject, Terminator, Thread, Initiator):
    def __init__(self, name=None, blocking=False, daemon=True, **kwargs):
        Thread.__init__(self, name=name, daemon=daemon)
        super().__init__(name=name, **kwargs)
        self.tdTerminate = False
        self.TDLock = RLock()
        self.setBlocking(blocking)
        self._accept = self._acceptHandle

    def end(self):
        self._accept = self._acceptHandle
        self.tdTerminate = True
        self.inputQueue.put(Sentinel())

    def setBlocking(self, blocking):
        with self.TDLock:
            if not type(blocking) is bool:
                raise TypeError(f'argument passed to object {self.getName()} setBlocking should be of type bool, is type {type(blocking)}.')
            self.blocking = blocking

    def run(self):
        self._accept = self._acceptQueue
        while not self.tdTerminate:
            with self.TDLock:
                try:
                    if not self.inputQueue.empty():
                        pkg = self.inputQueue.get(block=self.blocking)
                        if pkg and not isinstance(pkg, Sentinel):
                            self.handlePackage(pkg)
                except Exception as e:
                    self.logger.exception(e)
            time.sleep(.001)

    def _acceptQueue(self, package):
        self.inputQueue.put(package)

    def _acceptHandle(self, package):
        self.handlePackage(package)