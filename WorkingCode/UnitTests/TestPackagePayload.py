import datetime
import threading
import unittest

from Framework.BaseClasses.Commands import CommandPayload
from Framework.BaseClasses.Events import EventPayload
from Framework.BaseClasses.Package import Package, Payload
from Utils import ClassUtils as cu
from Utils import TimeUtils as tu


class pkgThread(threading.Thread):
    def __init__(self, outputList):
        threading.Thread.__init__(self)
        self.pkgs = 0
        self.outputList = outputList


    def run(self):
        while self.pkgs < 100:
            p = Package()
            self.outputList.append(p)
            self.pkgs += 1

class TestPackage(unittest.TestCase):
    def test_PackageID(self):
        pkgs = []
        p1 = pkgThread(pkgs)
        p2 = pkgThread(pkgs)
        p3 = pkgThread(pkgs)
        p1.start()
        p2.start()
        p3.start()
        startTime = datetime.datetime.now()
        while len(pkgs) < 300 and (startTime - datetime.datetime.now()) < datetime.timedelta(seconds=3):
            pass
        allIDs = [p.packageID for p in pkgs]
        uniqueIDS = set(allIDs)
        self.assertEqual(len(allIDs), len(uniqueIDS))


class TestPayload(unittest.TestCase):
    def test_Payload(self):
        pl1 = Payload('First', tu.nowEpoch(), foo=None, bar=1)
        self.assertEqual(pl1['source'], pl1.source)
        self.assertEqual(pl1['timestamp'], pl1.timestamp)
        self.assertEqual(pl1['foo'], pl1.foo)
        self.assertEqual(pl1['bar'], pl1.bar)
        del(pl1)

        pl2 = Payload('Second', something='Nothing', nothing='Something')
        self.assertEqual(pl2['something'], pl2.something)
        self.assertEqual(pl2['nothing'], pl2.nothing)
        self.assertEqual(pl2['source'], pl2.source)
        self.assertEqual(pl2['timestamp'], pl2.timestamp)

    def test_CmdEvt(self):
        cPld = CommandPayload(foo=0, bar=None)
        self.assertEqual('foo' in cPld.toDict().keys(), True)
        self.assertEqual('bar' in cPld.toDict().keys(), True)
        self.assertEqual('foobar' in cPld.toDict().keys(), False)
        self.assertEqual(cu.isPayload(cPld), True)

        ePld = EventPayload(foo=42, bar=None)
        self.assertEqual('foo' in ePld.toDict().keys(), True)
        self.assertEqual('bar' in ePld.toDict().keys(), True)
        self.assertEqual('foobar' in ePld.toDict().keys(), False)
        self.assertEqual(cu.isPayload(ePld), True)


