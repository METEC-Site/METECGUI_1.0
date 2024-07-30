import unittest
import multiprocessing as mp
import threading
import unittest

from Framework.BaseClasses.Events import EventTypes, EventPayload, Destination, Package, ChannelType
from Framework.BaseClasses.FrameworkObject import FrameworkObject
from Framework.BaseClasses.Subscriber import Subscriber
from Framework.BaseClasses.Worker import Worker
from UnitTests import TestAll as TA
from UnitTests.MainProcessGenerator import mainProcess


class MainEnder(Subscriber, Worker, Destination, FrameworkObject):
    def __init__(self, archiver, commandManager, dataManager, eventManager, name, namespace=None, stopSec = 1, **kwargs):
        Subscriber.__init__(self, name, archiver, commandManager, dataManager, eventManager, **kwargs)
        Destination.__init__(self, name, **kwargs)
        FrameworkObject.__init__(self, name, namespace)
        self.stopSec = stopSec

    def start(self):
        Destination.start(self)
        FrameworkObject.start(self)
        t = threading.Timer(self.stopSec, self.endProcess)
        t.start()

    def endProcess(self):
        print('Terminating Process')
        self.terminate = True
        pl = EventPayload(self.name, eventType=EventTypes.Shutdown, msg=f'Object {self.name} raised the shutdown event')
        endPkg = Package(self.name, payload=pl, channelType=ChannelType.Event)
        self.eventManager.accept(endPkg)
        i=-10

    def handlePackage(self, package):
        pass

class UnitTestMain(unittest.TestCase):

    @TA.CleanNamespace('test_Main')
    def test_Main(self):
         #todo: figure out why this is throwing an error.
        p = mp.Process(target=mainProcess)

        p.start()
        p.join(timeout=10)
        self.assertEqual(p.is_alive(), False)

