import tempfile
import tempfile
import unittest

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses.Events import EventTypes, EventPayload, Package, ChannelType
from Framework.BaseClasses.Subscriber import Subscriber
from Framework.Manager import EventManager
from UnitTests import TestAll as TA


class sub_Events(Subscriber):
    def __init__(self, name, archiver, eventManager: EventManager, subscriptions = []):
        Subscriber.__init__(self, name=name, archiver=archiver, commandManager=None, dataManager=None,
                            eventManager=eventManager, eventSubscriptions=subscriptions)
        self.name = name
        self.eventManager = eventManager
        self.packages = []

    def handlePackage(self, package):
        self.logger.info("package received")
        self.packages.append(package)

class pub():
    def __init__(self, name, eventManager):
        self.name = name
        self.eventManager=eventManager

    def publish(self):
        event = EventPayload(self.name, EventTypes.Default)
        evPkg = Package(self.name, payload=event, channelType=ChannelType.Event)
        self.eventManager.accept(evPkg)
        return evPkg


class TestEvents(unittest.TestCase):

    @TA.CleanNamespace('test_brokenObjects')
    def test_subscribeSourceEvents(self):
        with tempfile.TemporaryDirectory() as tDir:
            with DirectoryArchiver(name="sourceEventsArchiver", baseDir=tDir, template="tmp1_%Y%m%d", configFiles=[]) as da1:
                with EventManager.EventManager(da1, 'SubscriptionEventManager') as eventManager:
                    sSubs = [{'publisher': 'sourceA', 'events': [EventTypes.Connected]}]
                    s = sub_Events("subscribeSourceSub", archiver=da1, eventManager=eventManager, subscriptions=sSubs)
                    eventAPld = EventPayload('sourceA', EventTypes.Connected, msg='Source A Connected', foo='foo')
                    eventAPkg = Package('sourceA', payload=eventAPld, channelType=ChannelType.Event)
                    eventManager.accept(eventAPkg)

                    eventBPld = EventPayload('sourceB', EventTypes.Connected, msg='Source B Connected', bar='bar')
                    eventBPkg = Package('sourceB', payload=eventBPld, channelType=ChannelType.Event)
                    eventManager.accept(eventBPkg)

                    self.assertEqual(True, eventAPkg in s.packages)
                    self.assertEqual(False, eventBPkg in s.packages)

    @TA.CleanNamespace('test_subscribeSourceOnly')
    def test_subscribeSourceOnly(self):
            with tempfile.TemporaryDirectory() as tDir:
                with DirectoryArchiver(name="sourceOnlyArchiver", baseDir=tDir, template="tmp1_%Y%m%d", configFiles=[]) as da1:
                    eventManager = EventManager.EventManager(da1, "sourceOnlyEventManager")
                    sSubs = [{'publisher': 'sourceA'}]
                    s = sub_Events("sourceOnlySub", archiver=da1, eventManager=eventManager, subscriptions=sSubs)
                    eventAPld = EventPayload('sourceA', EventTypes.Connected, msg='Source A Connected', foo='foo')
                    eventAPkg = Package('sourceA', payload=eventAPld, channelType=ChannelType.Event)
                    eventManager.accept(eventAPkg)

                    eventBPld = EventPayload('sourceB', EventTypes.Connected, msg='Source B Connected', bar='bar')
                    eventBPkg = Package('sourceB', payload=eventBPld, channelType=ChannelType.Event)
                    eventManager.accept(eventBPkg)

                    self.assertEqual(True, eventAPkg in s.packages)
                    self.assertEqual(False, eventBPkg in s.packages)

    @TA.CleanNamespace('test_subscribeEventOnly')
    def test_subscribeEventOnly(self):
        with tempfile.TemporaryDirectory() as tDir:
            with DirectoryArchiver(name='subscribeEventsOnlyArchiver', baseDir=tDir, template="tmp1_%Y%m%d", configFiles=[]) as da1:
                eventManager = EventManager.EventManager(da1, "eventOnlyEventManager")
                sSubs = [{'publisher':'sourceA', 'events': []}]
                s = sub_Events("sub", archiver=da1, eventManager=eventManager, subscriptions=sSubs)
                eventAPld = EventPayload('sourceA', EventTypes.Connected, msg='Source A Connected', foo='foo')
                eventAPkg = Package('sourceA', payload=eventAPld, channelType=ChannelType.Event)
                eventManager.accept(eventAPkg)

                self.assertEqual(True, eventAPkg in s.packages)

    @TA.CleanNamespace('test_publish')
    def test_publish(self):
        with tempfile.TemporaryDirectory() as tDir:
            with DirectoryArchiver(name="publishArchiver", baseDir=tDir, template="tmp1_%Y%m%d", configFiles=[]) as da1:
                eventManager = EventManager.EventManager(da1, "publishEventManager")
                p = pub('pub', eventManager)
                subs = [{'publisher': 'pub', 'events': []}]
                s = sub_Events('publisherSub', archiver=da1, eventManager=eventManager, subscriptions=subs)
                pkg = p.publish()

                self.assertEqual(True, pkg in s.packages)