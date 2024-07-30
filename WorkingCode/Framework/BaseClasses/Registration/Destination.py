from abc import ABC, abstractmethod
from queue import Queue
from threading import Thread, RLock

from Framework.BaseClasses.LoggingObject import LoggingObject
from Framework.BaseClasses.NamedObject import NamedObject
from Framework.BaseClasses.StartStop import Initiator, Terminator
from Framework.Utils import ClassUtils as cu
from Framework.Utils import Exceptions as ex


class Destination(NamedObject, ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def handleIncomingPackage(self, package):
        raise NotImplementedError

    def _accept(self, package):
        self.handleIncomingPackage(package)

    def acceptPackage(self, package):
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

class ThreadedDestination(QueuedDestination, LoggingObject, Thread, Initiator, Terminator):
    def __init__(self, blocking=False, **kwargs):
        super().__init__(**kwargs)
        self.tdTerminate = False
        self.TDLock = RLock()
        self.setBlocking(blocking)
        self._accept = self._acceptHandle

    def start(self):
        self._accept = self._acceptQueue
        Thread.start(self)

    def end(self):
        self._accept = self._acceptHandle
        self.tdTerminate = True

    def setBlocking(self, blocking):
        with self.TDLock:
            if not type(blocking) is bool:
                raise TypeError(f'argument passed to object {self.getName()} setBlocking should be of type bool, is type {type(blocking)}.')
            self.blocking = blocking

    def run(self):
        while not self.tdTerminate:
            with self.TDLock:
                try:
                    if not self.inputQueue.empty():
                        pkg = self.inputQueue.get(block=self.blocking)
                        if pkg:
                            self.handleIncomingPackage(pkg)
                except Exception as e:
                    self.logger.exception(e)

    def _acceptQueue(self, package):
        self.inputQueue.put(package)

    def _acceptHandle(self, package):
        self.handleIncomingPackage(package)