import tempfile
import random
import tempfile
import unittest

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses.Events import Package, ChannelType
from Framework.BaseClasses.Subscriber import Subscriber
from Framework.Manager.DataManager import DataManager
from UnitTests import TestAll as TA
from Utils import TimeUtils as tu


class sub_Data(Subscriber):
    def __init__(self, name, archiver, dataManager:DataManager, subscriptions = [], **kwargs):
        Subscriber.__init__(self, name=name, archiver=archiver, commandManager=None, dataManager=dataManager,
                            eventManager=None, dataSubscriptions=subscriptions)
        self.name = name
        self.dataManager = dataManager
        self.packages = []

    def handlePackage(self, package):
        print("package received")
        self.packages.append(package)

class pub():
    def __init__(self, name, dataManager):
        self.name = name
        self.dataManager=dataManager
        dataRange = random.randint(4, 10)
        self.sourceTS = {'source': str,
                    'timestamp': 'datetime - UTC Epoch'}
        self.mdFields = {}
        for i in range(0, dataRange):
            self.mdFields[str(i)] = int

    def publish(self):
        d = {
            'source': self.name,
            'timestamp': tu.nowEpoch()
        }
        for i in self.mdFields.keys():
            d[str(i)] = i

        pkg = Package(self.name, payload=d, channelType=ChannelType.Data)
        self.dataManager.accept(pkg)
        return pkg


class TestData(unittest.TestCase):

    @TA.CleanNamespace('test_Subscribe')
    def test_subscribe(self):
        with tempfile.TemporaryDirectory() as tDir:
            with DirectoryArchiver(name="sourceEventsArchiver", baseDir=tDir, template="tmp1_%Y%m%d", configFiles=[]) as da1:
                dm = DataManager(da1, 'DataManager')
                subAll = sub_Data('sub1', archiver=da1, dataManager=dm)
                dm.subscribe(subAll)
                pub1 = pub('publisher1', dm)

                subInInit = sub_Data('sub2', archiver=da1, dataManager=dm, subscriptions=[{'publisherName': 'publisher1'}])
                pkg1 = pub1.publish()
                self.assertEqual(pkg1 in subAll.packages, True)
                self.assertEqual(pkg1 in subInInit.packages, True)

