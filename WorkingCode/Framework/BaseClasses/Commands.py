#INDOCS
import functools
import logging
from abc import ABC
from enum import Enum
from threading import RLock

from Framework.BaseClasses.Destination import ThreadedDestination
from Framework.BaseClasses.LoggingObject import LoggingObject
from Framework.BaseClasses.Package import Payload
from Utils import ClassUtils as cu
from Utils import TimeUtils as tu


class CommandLevels(Enum):
    """Importance of command"""
    Immediate       = 0
    Noncritical        = 1

class CommandPayload(Payload):
    __bases__ = [Payload]
    """sets values for payloads within command packages"""
    def __init__(self, commandLevel=CommandLevels.Noncritical, onBehalfOfID=None, commandID=None, destination=None,
                 source=None, sourceMethod=None, command=None, args=[], kws={}, timestamp=None, **kwargs):
        Payload.__init__(self, source, timestamp, commandLevel=commandLevel, onBehalfOfID=onBehalfOfID,
                         commandID=commandID, destination=destination, sourceMethod=sourceMethod,
                         command=command, args=args, kws=kws, **kwargs)
        """
        self.commandLevel: Command level for Command Payload. Default set to Noncritical.
        self.onBehalfOfID:  Default set to None
        self.commandID: commandID set through Command Manager. Default set to None.
        self.destination: Destination of command.
        self.source: Source where command comes from.
        self.sourceMethod: Method sent from source.
        self.command: command passed with payload.
        self.args: Arguments to be passed with payload.
        self.kwargs: Keyword Arguments to be passed with payload.
        self.ts: Time Stamp.
        
        .. seealso::
            
        """

    def toDict(self):
        d = {
            'timestamp': self.ts,
            'source': self.source,
            'sourceMethod': self.sourceMethod,
            'destination': self.destination,
            'command': self.command,
            'commandLevel': self.commandLevel,
            'onBehalfOfID': self.onBehalfOfID,
            'commandID': self.commandID,
            'args': self.args,
            'kws': self.kws
        }
        d = {**d, **self.map}
        return d


class ResponsePayload(Payload):
    """sets values for payloads within response packages"""
    def __init__(self, source=None, destination=None, ret=None, commandID=None, responseLevel=None, ts=None,
                       **kwargs):
        if ts == None:
            ts = tu.nowEpoch()
        Payload.__init__(self, source=source, ts=ts, destination=destination, ret=ret, commandID=commandID,
                         responseLevel=responseLevel, **kwargs)
        """
        self.responseLevel: stores the response level passed through the constructor default is Whenever.
        self.source: source of Command.
        self.destination: destination that Command is going to.
        self.commandID: commandID passed through constructor.
        self.ret: return passed through constructor.
        self.ts: timestamp.
        """
        # self.source = source
        # self.destination = destination
        # self.ret = ret
        # self.commandID = commandID
        # self.responseLevel = responseLevel
        # self.ts = ts
        pass

    def toDict(self):
        d = dict(timestamp=self.ts, responseLevel=self.responseLevel, source=self.source,
                        destination=self.destination, commandID=self.commandID, ret=self.ret)
        return d


class CommandClass(ThreadedDestination, LoggingObject, ABC):
    """The CommandClass is utilized when data is being sent through a Command"""
    # L(CC) = [CC, ABC]
    instances = 0
    def __init__(self, name=None, commandManager=None, **kwargs):
        """
        self.name: Name of the Command Manager.
        self._visibleCommands: List of all commands visible.
        self.CommandManager: The current Command Manager that's set.
        """
        super().__init__(name=name, commandManager=commandManager, **kwargs)
        # _visibleCommands is a list of all functions that are tagged with the @commandMethod decorator in the class definition.
        self._visibleCommands = []
        for singleFunc in dir(self):
            try:
                if '__isCommand__' in dir(self.__getattribute__(singleFunc)):
                    self._visibleCommands.append(singleFunc)
            except Exception as e:
                self.logger.exception(e)
        self.commandManager=None
        self.setCommandManager(commandManager)
        if not self.commandManager is None:
            self.commandManager.registerCommandClass(self)
        self.transactions = {}
        self.lock = RLock()

    def setCommandManager(self, commandManager):
        """If there isn't a previously set Command Manager than setCommandManager sets one."""
        if cu.isCommandManager(commandManager):
            self.commandManager = commandManager
            return True
        else:
            logging.warning(f'Command Class Object {self.getName()} expected commandManager to be of type CommandManager, '
                            f'got {type(commandManager)} instead')
            return False

    def getCCMetadata(self):
        """returns metadata for the Command Class"""
        cpMetadata = {
            'name': self.getName(),
            'commands': self._visibleCommands,
            'object': self
        }
        return cpMetadata

    def executeCommand(self, package):
        """
        executes a command
        if there is no destination name or command then it sends a response and returns the command status No Such Method
        else it locks a thread and creates data for a return package
        it then emits this return package sending it back to the source to handle the response.
        """
        commandPL = package.payload
        onBehalfOfID = commandPL['onBehalfOfID']
        commandLevel = commandPL['commandLevel']
        commandID = commandPL['commandID']
        destination = commandPL['destination']
        source = commandPL['source']
        sourceMethod = commandPL['sourceMethod']
        command = commandPL['command']
        args = commandPL['args']
        kws = commandPL['kws']

        # TODO: unnecessary? Should CommandManager do this check?
        if not self.getName() == destination or not command in self._visibleCommands:
            returnPackage = self.commandManager.createResponsePackage(self.getName(), source, CommandStatus.NoSuchMethod, onBehalfOfID=commandID)
            self.commandManager.accept(returnPackage)
            return CommandStatus.NoSuchMethod

        with self.lock:
            method = getattr(self, command)
            method.__dict__['_onBehalfOfID'][self.getName()]=commandID
            ret = method(*args, **kws)
        returnPackage = self.commandManager.createResponsePackage(self.getName(), source, ret, commandID=commandID)
        self._emitResponse(returnPackage)
        return ret

    def _emitResponse(self, package):
        if self.commandManager:
            # This always returns None if the command manager is operating in threaded mode.
            self.commandManager.accept(package)
        else:
            logging.log(level=logging.INFO, msg="No Command Manager set for {}. Cannot send package.".format(self.getName()))
        pass

    def _emitCommand(self, package, timeout=None):
        """
        if a commandManager is set it calls accept within the destination base class
        else: throw error that no Command Manager is set.
        """
        if self.commandManager:
            self.commandManager.accept(package)
            responsePkg = self.commandManager.getResponse(package, timeout)
            if cu.isPackage(responsePkg):
                responsePl = responsePkg.payload
                response = responsePl['ret']
            else:
                response = responsePkg
            return response
        else:
            logging.log(level=logging.INFO, msg="No Command Manager set for {}. Cannot send package.".format(self.getName()))
        pass

    def createCommandPackage(self, sourceFunction, destination, destinationCommand, args=[], kwargs={},
                             commandLevel=CommandLevels.Immediate):
        """
        If there is a Command Manager it creates a Command Package to be returned.
        else it throws an error for no Command Manager being set/
        """
        onBehalfDict = getattr(self, sourceFunction).__dict__.get('_onBehalfOfID', {})
        onBehalfOfID = onBehalfDict.get(self.getName(), None)
        if self.commandManager:
            package = self.commandManager.createCommandPackage(self.getName(), sourceFunction, destination, destinationCommand,
                                                               args, kwargs, onBehalfOfID=onBehalfOfID, commandLevel=commandLevel)
            return package
        else:
            logging.log(level=logging.INFO,
                        msg="No Command Manager set for {}. Cannot make command package".format(self.getName()))

# Decorator for externally visible/commandable methods
def CommandMethod(func):
    """The CommandMethod function is utilized when trying to make external methods visible"""
    @functools.wraps(func)
    def returnFunc(*args, **kwargs):
        """returns the function and its parameters"""
        # TODO: Check if this is the functionality desired.
        # I want so that if two threads attempt to call the same method on one object, it blocks, but if the call is
        # on different objects, both could execute at the same time.

        ret = func(*args, **kwargs)
        return ret
        # return func(*args, **kwargs)

    ret = returnFunc
    ret.__dict__['_onBehalfOfID'] = {}
    ret.__dict__['__isCommand__'] = True
    ret.__cust_args__ = []
    ret.__cust_kwargs__ = {}
    return ret

class CommandStatus(Enum):
    """sets the CommandStatus"""
    Received = 0
    Issued = 1
    Completed = 2
    Failed = 3
    NoSuchMethod = 4