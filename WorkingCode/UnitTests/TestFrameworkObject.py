import tempfile
import unittest

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses.FrameworkObject import FrameworkObject
from Framework.Manager.CommandManager import CommandManager
from Framework.Manager.DataManager import DataManager
from Framework.Manager.EventManager import EventManager
from Framework.Manager.ObjectManager import ObjectManager
from UnitTests import TestAll as TA
from UnitTests.TestEvents import sub_Events
from Utils import ClassUtils as cu


class TestObject(FrameworkObject):
    def __init__(self, name):
        FrameworkObject.__init__(self, name)

    def start(self):
        pass

    def end(self):
        FrameworkObject.end(self)
        self._onExitCleanup()

    def accept(self, package):
        pass

    def handlePackage(self, package):
        pass

    def _onExitCleanup(self):
        ObjectManager.unregisterObject(self.name)
        pass


class TestObject2(FrameworkObject):
    def __init__(self, name):
        FrameworkObject.__init__(self, name)

    def start(self):
        pass

    def end(self):
        FrameworkObject.end(self)
        self._onExitCleanup()

    def accept(self, package):
        pass

    def handlePackage(self, package):
        pass

    def _onExitCleanup(self):
        ObjectManager.unregisterObject(self.name)
        pass

class TestObjectChild(TestObject, TestObject2):
    def __init__(self, name):
        TestObject.__init__(self, name)
        TestObject2.__init__(self, name)

class TestFrameworkManager(unittest.TestCase):
    @TA.CleanNamespace('test_brokenObjects')
    def test_brokenObjects(self):
        with tempfile.TemporaryDirectory() as tDir:
            with DirectoryArchiver(name="unittestArchiver", baseDir=tDir, template="tmp1_%Y%m%d",
                                   configFiles=[]) as da1:
                eventManager = EventManager(da1, "eventManager")
                try:
                    broken1 = sub_Events(1, eventManager, None)
                    oneCorrect = True
                except Exception as e:
                    oneCorrect = False
                self.assertEqual(oneCorrect, False)

                try:
                    e2 = EventManager(da1, 'eventManager')
                    twoCorrect = True
                except:
                    twoCorrect = False
                self.assertEqual(twoCorrect, False)

    @TA.CleanNamespace('test_isFrameworkObject')
    def test_isFrameworkObject(self):
        fo = TestObject('FO')
        isFO = cu.isFrameworkObject(fo)
        self.assertEqual(isFO, True)

        fo.end()
        fo.end()


    @TA.CleanNamespace('test_Managers')
    def test_Managers(self):
        cm = CommandManager(None, 'CommandManager')
        dm = DataManager(None, 'DataManager')
        em = EventManager(None, 'EventManager')
        self.assertEqual(True, ObjectManager.nameInRegistry(cm.name))
        self.assertEqual(True, ObjectManager.nameInRegistry(dm.name))
        self.assertEqual(True, ObjectManager.nameInRegistry(em.name))
        cm.end()
        dm.end()
        em.end()
        self.assertEqual(False, ObjectManager.nameInRegistry(cm.name))
        self.assertEqual(False, ObjectManager.nameInRegistry(dm.name))
        self.assertEqual(False, ObjectManager.nameInRegistry(em.name))

    @TA.CleanNamespace('test_inheritence')
    def test_inheritence(self):
        to = TestObjectChild('TestObject1')
        to2 = TestObjectChild('TestObject2')
        ObjectManager.registerObject(to)
        ObjectManager.registerObject(to2)
        self.assertEqual(True, ObjectManager.nameInRegistry('TestObject1'))
        self.assertEqual(True, ObjectManager.nameInRegistry('TestObject2'))
        to.end()
        self.assertEqual(False, ObjectManager.nameInRegistry('TestObject1'))

    @TA.CleanNamespace('test_end')
    def test_end(self):
        to = TestObject('Object1')
        ObjectManager.registerObject(to)
        self.assertEqual(True, ObjectManager.nameInRegistry('Object1'))
        to.end()
        self.assertEqual(False, ObjectManager.nameInRegistry('Object1'))
        ObjectManager.endNamespace()

        self.assertEqual(False, ObjectManager().nameInRegistry('Object1'))
        ObjectManager().registerObject(to)
        self.assertEqual(True, ObjectManager().nameInRegistry('Object1'))

    @TA.CleanNamespace('test_end')
    def testEndAgain(self):
        # this only works if running test_end right before this.
        self.assertEqual(False, ObjectManager().nameInRegistry('Object1'))
        to = TestObject('Object1')
        ObjectManager().registerObject(to)
        self.assertEqual(True, ObjectManager().nameInRegistry('Object1'))
        to.end()
