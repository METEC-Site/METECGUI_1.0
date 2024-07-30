import logging
from threading import RLock, Event

import Framework.BaseClasses.Commands as cmd
import Framework.BaseClasses.Manager
import Utils.TimeUtils as tu
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Commands import CommandLevels
from Framework.BaseClasses.Destination import ThreadedDestination
from Framework.BaseClasses.Package import Package
from Framework.Manager.ObjectManager import ObjectManager
from Utils.ClassUtils import isCommandClass, isArchiver, isProxy

__docformat__ = 'reStructuredText'

class CommandManager(Framework.BaseClasses.Manager.CommandManager_Base, ThreadedDestination):
    """ Handles commands and responses """
    def __init__(self, archiver, processStopper=None, name=None, requestTimeout = 1.0, **kwargs):
        """
        self.name: Name of the Command Manager.
        self.commandClasses: Object of all Command Classes available.
        self.transaction:  Object of all transactions that have gone through the Command Manager.
        self.cachedTransactions: Object of all cached transactions that have gone through the Command Manager.
        self.commandID: The commandID gets passed to each payload for the command and response
        self.archiver: holds an archiver when set by the registerArchiver function
        """
        if not name:
            name = "CommandManager"
        ThreadedDestination.__init__(self, name=name)
        # Metadata for command generators and processors.
        self.commandClasses = {}
        self.transactions = {}
        self.cachedTransactions = {}
        self.commandID = 0

        self.requestTimeout = requestTimeout

        self.proxy = None

        self.archiver = archiver
        self.registerArchiver(self.archiver)

        self.lock = RLock()
        if processStopper:
            self.processStopper = processStopper
        else:
            logging.debug(f'Event Manager {self.name} was not passed a processStopper event.')
            self.processStopper = Event()

    def subscribe(self, obj, objName, namespace):
        """

        Subscription will be a dictionary most likely,

        :param obj:
        :param objName:
        :param subscription:
        :return:
        """
        pass

    def registerArchiver(self, archiver):
        """
        Creates channel to send all Commands and Responses to specified Archive (ar).
        """

        if isArchiver(archiver):
            self.archiver = archiver
            self.archiver.createChannel(self.name, channelType=ChannelType.Command)
            archiver.CommandManager = self
            for cc, metadata in self.commandClasses.items():
                name = metadata['name']
                archiver.createChannel(name, ChannelType.Command)
                archiver.createChannel(name, ChannelType.Response)
        else:
            logging.warning(
                f'Object {archiver} is not of type Archiver, cannot register with CommandManager named {self.name}')

    def registerProxy(self, proxyObject):
        if not isProxy(proxyObject):
            return False
        self.proxy = proxyObject

    def registerCommandClass(self, cc):
        """
        Checks if command class passed is actually a command class.
        Appends data to commandClasses object if it isn't already there.
        Creates a channel to archive data too if an archiver is being used.
        """
        #TODO: handle multiple registration of the same class
        if isCommandClass(cc):
            ccName = cc.getName()
            if not ccName in self.commandClasses.keys():
                ccMetadata = {
                    'name': cc.getName(),
                    'commands': cc._visibleCommands,
                    'object': cc
                }
                self.commandClasses[ccName] = ccMetadata
            elif not self.commandClasses[ccName]['object'] == cc:
                raise NameError(f"Cannot register two Command Classes with same name: {ccName}")
            cc.setCommandManager(self)
            if self.archiver:
                self.archiver.createChannel(ccName, ChannelType.Command)
                self.archiver.createChannel(ccName, ChannelType.Response)
            ObjectManager.registerObject(cc)

    def handlePackage(self, package):
        """
            1.) Determines whether package channel is a Command or Response.
            2.) Calls issueCommand or issueResponse based on the above conditional.
        """
        if package.channelType == ChannelType.Command:
            try:
                self.issueCommand(package)
            except NameError as e:
                logging.error(e)
        if package.channelType == ChannelType.Response:
            self.issueResponse(package)

    def getCommandID(self):
        """
           Returns commandID.
        """
        with self.lock:
            self.commandID = self.commandID + 1
            ret = self.commandID
        return ret

    def createCommandPackage(self, sourceName, sourceFunction, destination, destinationCommand, args=[], kwargs={},
                             onBehalfOfID=None, commandLevel=cmd.CommandLevels.Immediate):
        """Creates a command package with a command payload."""
        # TODO: Check if source obj has registered with the command manager, and if sourceFunction is in the publinc methods.
        payload = cmd.CommandPayload(source=sourceName, sourceMethod=sourceFunction, destination=destination,
                                 command=destinationCommand, args=args, kwargs=kwargs, onBehalfOfID=onBehalfOfID,
                                 commandLevel=commandLevel, commandID=self.getCommandID())
        package = Package(source=self.name, payload=payload, channelType=ChannelType.Command)
        return package

    def createResponsePackage(self, responseSource, responseDestination, ret, commandID):
        """Creates a package with a response payload."""
        payload = cmd.ResponsePayload(source=responseSource, destination=responseDestination, ret=ret, commandID=commandID)
        package = Package(source=self.name, channelType=ChannelType.Response, payload=payload)
        return package

    def getResponse(self, commandPackage, timeout=None):
        t = tu.nowEpoch()
        commandPl = commandPackage.payload
        commandID = commandPl.commandID
        transaction = None
        if timeout is None:
            timeout=self.requestTimeout # 2 second timeout by default if nt specified. .
        while not tu.nowEpoch() - t > timeout and not transaction:
            transaction = self.cachedTransactions.get(commandID, None)
        if transaction:
            response = transaction['responsePackage']
            return response
        else:
            #TODO: log that a response wasn't received?
            return False

    def issueCommand(self, package):
        """Send package to destination."""

        tid = package.payload['commandID']

        # Keep track in an internal dictionary of the command package and a response, if any. Status is that the command has been received.
        currentTransaction = self.transactions[tid] = {}
        currentTransaction['commandPackage'] = package
        currentTransaction['responsePackage'] = None
        currentTransaction['status'] = cmd.CommandStatus.Received
        commandPL = package.payload

        commandDest = commandPL['destination']
        commandSource = commandPL['source']
        commandDestinationMethod = commandPL['command']
        if self.proxy:
            self.proxy.accept(package)
        if commandDest in self.commandClasses.keys() and commandDestinationMethod in self.commandClasses[commandDest]['commands']:
            obj = self.commandClasses[commandDest]['object']
            self.archive(package)
            if commandPL['commandLevel'] == CommandLevels.Noncritical:
                return obj.accept(package)
            elif commandPL['commandLevel'] == CommandLevels.Immediate:
                return obj.executeCommand(package)
        else:
            raise NameError(f"Command sent to destination {commandDest} but no command class {commandDest} is registered to the Command Manager named {self.name}")

    def issueResponse(self, package):
        """
        Sends a response to the source.

        Removes commandID from cachedTransactions.

        adds package to transaction['responsePackage']

        sets transaction status to completed

        archives package

        caches transaction
        """
        responsePayload = package.payload
        #In this context, onBehalfOfID is the ID corresponding to the commandID of the command that needs this response.
        commandID = responsePayload['commandID']
        transaction = self.transactions[commandID]
        transaction['responsePackage'] = package
        self.archive(package)
        transaction = self.transactions.pop(commandID)
        self.cachedTransactions[commandID] = transaction
        if self.proxy:
            self.proxy.accept(package)

    def archive(self, package):
        """Calls _archive passing package as a parameter."""
        self._archive(package)

    def _archive(self, package):
        """If there is a directory to, archive to archive the package."""
        if self.archiver:
            self.archiver.accept(package)
        else:
            logging.info(str(package))
            pass

    def queryCommandProcessorMetaData(self):
        pass
        # cpMetadata = deepcopy(self.commandDestinations[cpName]) if cpName in self.commandDestinations.keys() else None
        # return cpMetadata

    def queryTransactionState(self, commandID):
        pass