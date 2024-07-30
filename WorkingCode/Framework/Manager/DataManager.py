import logging
import threading

from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Destination import ThreadedDestination
from Framework.BaseClasses.Manager import DataManager_Base as dm
from Framework.Manager.ObjectManager import ObjectManager
from Utils import ClassUtils as cu


class DataManager(dm, ThreadedDestination):
    def __init__(self, archiver, processStopper=None, name='DataManager', **kwargs):
        """Creates a Data Manager"""
        ThreadedDestination.__init__(self, name=name)
        dm.__init__(self, name)
        self.subscriptions = {}
        self.subRecords = []
        self.registerArchiver(archiver)
        ObjectManager.registerObject(self)
        if processStopper:
            self.processStopper = processStopper
        else:
            logging.debug(f'Data Manager {self.getName()} was not passed a processStopper event.')
            self.processStopper = threading.Event()

    def registerArchiver(self, archiver):
        if cu.isArchiver(archiver):
            # register the archiver to all channels that the data manager receives.
            self.archiver = archiver
            self.subscribe(archiver)
        else:
            logging.warning(f'Object {archiver} is not of type Archiver, cannot register with DataManager named {self.name}')

    def registerProxy(self, proxyObject):
        if not cu.isProxy(proxyObject):
            return False
        self.proxy = proxyObject
        # dataSubscriptions = self.proxy.getDataSubscriptions()
        # if dataSubscriptions:
        #     for singleSubscription in dataSubscriptions:
        #         self.subscribe(self.proxy, **singleSubscription)

    def getSubRecords(self):
        return self.subRecords

    def subscribe(self, subscriberObject, subscriberObjName: str=None, publisherName: str=None):
        """{
            'namespace': 'namespace'
            'publisher': 'publisherName'
        }

        :param subscriberObject:
        :param subscriberObjName:
        :param publisherNamespace:
        :param publisherName:
        :return:

        The subscriptions will be added according to the following rules:
            1) If no namespace is supplied, the default process namespace in which the DataManager resides will be used.
            2) If the publisher is not supplied, the object will be subscribed to all publishers.
            4) If the objName is not supplied, then the object will be registered under obj.name.
        """

        if subscriberObjName is None:
            subscriberObjName = subscriberObject.getName()
        if publisherName is None:
            publisherName = 'SOME_KEY_FOR_ALL_PUBLISHERS'
        if not publisherName in self.subscriptions.keys():
            self.subscriptions[publisherName] = {}
        # TODO: add check here for duplicate/conflicting subscriber
        self.subscriptions[publisherName][subscriberObjName] = subscriberObject
        subRecord = {subscriberObjName: {
            'publisher': publisherName
        }}
        self.subRecords.append(subRecord)

    def handlePackage(self, package):
        if package.channelType == ChannelType.Data:
            self.publish(package)

    def publish(self, package):
        publisher = package.source

        pubs = self.subscriptions.get(publisher, {})
        allPubs = self.subscriptions.get('SOME_KEY_FOR_ALL_PUBLISHERS', {})
        allSubs = set()
        for singleSub in pubs.values():
            allSubs.add(singleSub)
        for singleSub in allPubs.values():
            allSubs.add(singleSub)
        for sub in allSubs:
            sub.accept(package)