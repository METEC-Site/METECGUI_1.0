#INDOCS

from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Events import EventTypes
# from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses.Manager import EventManager_Base as em
from Framework.Manager.ObjectManager import ObjectManager
from Utils import ClassUtils as cu


class EventManager(em):
    """ A manager class that handles events raised by publishers and that sends those events to subscribers if applicable.

        The event manager's purpose is to sheppard events from events, raised by a publisher object, and putting those
        event packages on the accept method of the subscribers. Subscribers must be subscribed to either events from that
        publisher, or to events of that event type in order to receive those raised events.


        :ivar name: Unique name for this object. Must be unique across all objects in this project.
        :ivar subscribers: A list of subscriber objects. Each will be registered using self.registerSubscriber method.
        :type name: str
        :type subscribers:

    """
    def __init__(self, archiver, name='EventManager', **kwargs):
        em.__init__(self, name)
        self.name = name
        # self.pubSub = {}
        self.subRecords = []
        self.subscriptions = {}

        self.archiver = None
        self.registerArchiver(archiver)
        self.proxy = None
        ObjectManager().registerObject(self)

    def registerProxy(self, proxyObject):
        if not cu.isProxy(proxyObject):
            return False
        self.proxy = proxyObject
        # dataSubscriptions = self.proxy.getEventSubscription()
        # if dataSubscriptions:
        #     for singleSubscription in dataSubscriptions:
        #         self.subscribe(self.proxy, **singleSubscription)

    def registerArchiver(self, archiver):
        if cu.isArchiver(archiver):
            self.archiver = archiver
            self.archiver.createChannel(self.name, channelType=ChannelType.Event)
        else:
            self.logger.warning(f'Object {archiver} is not of type Archiver, cannot register with EventManager named {self.getName()}')

    def getSubRecords(self):
        return self.subRecords

    def subscribe(self, obj, objName: str=None, publisher: str=None, events: list=None):
        """{
            'namespace': 'namespace'
            'publisher': 'publisherName',
            'events': ['eventType1', 'eventType2']
        }

        The subscriptions will be added according to the following rules:
            1) If no namespace is supplied, the default process namespace in which the eventManager resides will be used.
            2) If the publisher is not supplied, the object will be registered to all events of the specified event type
            3) If the events are not supplied, then each event in the EventTypes enum will be subscribed to.
            4) If the objName is not supplied, then the object will be registered under obj.name."""
        # TODO: Undo comment after switching to new subscriber version is complete.
        # if not cu.isSubscriber(obj):
        #     self.logger.info(f'Event Manager \'{self.name}\' tried to add a subscription '
        #                  f'to publisher {publisher}, but object {obj} is not a subscriber object.')
        #     return False
        if objName is None:
            objName = obj.name
        if publisher is None:
            publisher = 'SOME_KEY_FOR_ALL_PUBLISHERS'
        if events is None:
            # subscribe to all events from a publisher no events are supplied.
            events = [event for event in EventTypes]
        if type(events) is list and len(events) == 0:
            events = [event for event in EventTypes]
        for singleEvent in events:
            # second key level is eventType.
            if self.subscriptions.get(singleEvent, None) is None:
                self.subscriptions[singleEvent] = {}
            # third key level is publisher.
            if self.subscriptions[singleEvent].get(publisher, None) is None:
                self.subscriptions[singleEvent][publisher] = {}
            # TODO: add check here for duplicate/conflicting subscriber
            self.subscriptions[singleEvent][publisher][objName] = obj
        subRecord = {objName: {
            'publisher': publisher,
            'events': events
        }}
        self.subRecords.append(subRecord)
        # TODO: Add checks for event types, and maybe publishers.

    def publish(self, package):
        # Pubilsh a package to a subscriber if the subscriber is listening for events from that publisher AND EITHER
        # A) The event type is in the subscription pool of listening events from that publisher or
        # B) the event pool is empty (signalling that every event should be listened to).

        self.archive(package)
        pkgSource = package.source
        pld = package.payload
        event = package.payload
        publisher = package.source
        eventType = event.eventType

        if pld.eventType == EventTypes.Shutdown:
            self.logger.info(f'Shutdown event received by EventManager {self.getName()}; Setting global process stopper signal.')
            stopper = ObjectManager.getStopper()
            stopper.set()

        # TODO: add checks regarding the outcome of the get method.
        pldType = self.subscriptions.get(eventType, {})
        pub = pldType.get(publisher, {})
        allPublish = self.subscriptions.get('SOME_KEY_FOR_ALL_PUBLISHERS', {})
        uniqueSubs = set([*list(pub.values()), *list(allPublish.values())])
        for sub in uniqueSubs:
            sub.accept(package)

    def archive(self, package):
        if self.archiver:
            self.archiver.accept(package)
            # pkgFromEM = Package(self.name, payload=package.payload, channelType=ChannelType.Event)
            # self.archiver.accept(pkgFromEM)

    def handlePackage(self, package):
        try:
            if package.channelType == ChannelType.Event:
                self.publish(package)
        except Exception as e:
            self.logger.exception(f'Could not publish event due to exception {e}')
