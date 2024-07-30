import logging
from abc import ABC, abstractmethod

from Framework.BaseClasses.Commands import CommandLevels
from Framework.BaseClasses.Destination import ThreadedDestination
# from Framework.BaseClasses.FrameworkObject import FOMetaclass, FrameworkObject # commented out to transition to Frameworkv2
from Framework.BaseClasses.Registration.FrameworkRegistration import FrameworkObject
from Utils import ClassUtils as cu


class Proxy_Base(ThreadedDestination, FrameworkObject, ABC):
    pass

class DataManager_Base(ThreadedDestination, FrameworkObject, ABC):

    def __init__(self, name, **kwargs):
        ThreadedDestination.__init__(self, name=name, **kwargs)
        FrameworkObject.__init__(self, name=name)
        self.eventManager = None
        self.commandManager = None

    @abstractmethod
    def subscribe(self, obj, objName, subscription):
        pass

    def setEventManager(self, eventManager):
        if not cu.isEventManager(eventManager):
            logging.info(f'Object named {self.getName()} attempted to add eventManager {eventManager}, but this object '
                         f'was not of type EventManager')
            return False
        self.eventManager = eventManager
        return True

    def setCommandManager(self, commandManager):
        if not cu.isCommandManager(commandManager):
            logging.info(f'Object named {self.getName()} attempted to add dataManager {commandManager}, but this object '
                         f'was not of type CommandManager')
            return False
        self.commandManager = commandManager
        return True

    def setDataManager(self, dataManager):
        if not cu.isDataManager(dataManager):
            logging.info(f'Object named {self.getName()} attempted to add dataManager {dataManager}, but this object '
                         f'was not of type DataManager')
            return False
        self.dataManager = dataManager
        return True

class EventManager_Base(ThreadedDestination, FrameworkObject, ABC):

    def __init__(self, name, **kwargs):
        ThreadedDestination.__init__(self, name=name, **kwargs)
        FrameworkObject.__init__(self, name=name)
        self.dataManager=None
        self.commandManager=None

    @abstractmethod
    def subscribe(self, obj, objName, subscription):
        pass

    @abstractmethod
    def registerArchiver(self, archiver):
        pass

    @abstractmethod
    def publish(self, package):
        pass

    @abstractmethod
    def archive(self, package):
        pass

    @abstractmethod
    def registerProxy(self, proxyObject):
        pass

    def setEventManager(self, eventManager):
        if not cu.isEventManager(eventManager):
            logging.info(f'Object named {self.getName()} attempted to add eventManager {eventManager}, but this object '
                         f'was not of type EventManager')
            return False
        self.eventManager = eventManager
        return True

    def setCommandManager(self, commandManager):
        if not cu.isCommandManager(commandManager):
            logging.info(f'Object named {self.getName()} attempted to add dataManager {commandManager}, but this object '
                         f'was not of type CommandManager')
            return False
        self.commandManager = commandManager
        return True

    def setDataManager(self, dataManager):
        if not cu.isDataManager(dataManager):
            logging.info(f'Object named {self.getName()} attempted to add dataManager {dataManager}, but this object '
                         f'was not of type DataManager')
            return False
        self.dataManager = dataManager
        return True

class CommandManager_Base(ThreadedDestination, FrameworkObject, ABC):
    """
    .. _command-manager-base-class:

    This class is intended to act as a base class for inherited subclasses.

    When a subclass inherits from CommandManager, it **must** implement the following abstract methods:

        * __init__
        * issueCommand
        * queryTransactionState
        * queryCommandProcessorMetadata
        * ceateCommandPackage
        * createResponsePackage

    .. note::
        The :ref:`isCommandManager <is-command-manager>` method checks to see if this class appears as any of the subclass's bases.
    """

    def __init__(self, name, **kwargs):
        ThreadedDestination.__init__(self, name, **kwargs)
        FrameworkObject.__init__(self, name=name)
        self.eventManager = None
        self.dataManager = None

    @abstractmethod
    def subscribe(self, obj, objName, subscription):
        pass

    @abstractmethod
    def issueCommand(self, package):
        pass

    @abstractmethod
    def queryTransactionState(self, commandID):
        pass

    @abstractmethod
    def queryCommandProcessorMetaData(self):
        pass

    @abstractmethod
    def createCommandPackage(self, sourceName, sourceFunction, destination, destinationCommand, args=[], kwargs={},
                             onBehalfOfID=None, commandLevel=CommandLevels.Immediate):
        pass

    @abstractmethod
    def createResponsePackage(self, responseSource, responseDestination, ret, commandID):
        pass

    @abstractmethod
    def registerProxy(self, proxy):
        pass

    def setEventManager(self, eventManager):
        if not cu.isEventManager(eventManager):
            logging.info(f'Object named {self.getName()} attempted to add eventManager {eventManager}, but this object '
                         f'was not of type EventManager')
            return False
        self.eventManager = eventManager
        return True

    def setCommandManager(self, commandManager):
        if not cu.isCommandManager(commandManager):
            logging.info(f'Object named {self.getName()} attempted to add dataManager {commandManager}, but this object '
                         f'was not of type CommandManager')
            return False
        self.commandManager = commandManager
        return True

    def setDataManager(self, dataManager):
        if not cu.isDataManager(dataManager):
            logging.info(f'Object named {self.getName()} attempted to add dataManager {dataManager}, but this object '
                         f'was not of type DataManager')
            return False
        self.dataManager = dataManager
        return True