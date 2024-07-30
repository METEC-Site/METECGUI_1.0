import collections
import logging
import pickle
import queue
import threading
from enum import Enum
from typing import Optional

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses import Events
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Destination import Destination
from Framework.BaseClasses.Manager import Proxy
from Framework.BaseClasses.Package import Package
from Framework.BaseClasses.Worker import Worker
from Framework.Manager.CommandManager import CommandManager
from Framework.Manager.DataManager import DataManager
from Framework.Manager.EventManager import EventManager
from Framework.Proxy import ProxyHeader as ph
from Framework.Proxy import ProxySerializer as ps
from Framework.Proxy.Listeners import ListenerFactory as lf
from Utils import ClassUtils as cu


class SourceNotRegistered(Exception):
    pass


_EXAMPLE_SOURCES = {
    "sourceName": {
        "sourceID": 1,
        "connection": "[proxyName]",
        "metadata": collections.OrderedDict([('data', 'B'),
                                             ('eventType', '4s'),
                                             ('msg', '7s'),
                                             ('source', '7s'),
                                             ('timestamp', 'd')]),  # metadata of latest serialized data packet

        'fmt': "B4s7s7sd"
    }
}
# _EXAMPLE_CONNECTIONS = {
#     "[proxyName]": {
#         "connection": tcp.TCPconnector,
#         'conType': 'tcp',
#         'subscribedSources': []
#
#     },
#     "[proxyName2]": {
#         "connection": "[Lora]",
#         'conType': 'lora',
#         'subscribedSources': []
#     }
# }


_EXAMPLE_INTERFACES = {
    'module': 'Framework.Proxy.Connectors.TCPInterface'
}

# API
class ProxyController(Proxy, Worker, Destination):

    def __init__(self,
                 archiver: Optional[DirectoryArchiver] = None,
                 commandManager: Optional[CommandManager] = None,
                 dataManager: Optional[DataManager] = None,
                 eventManager: Optional[EventManager] = None,
                 name: str = None,
                 interfaces = []
                 ):
        Destination.__init__(self, name)
        Worker.__init__(self, archiver, commandManager, dataManager, eventManager, name)
        # Register with Managers and ask for sources and subscriptions where applicable.
        self.eventManager = None
        self.dataManager = None
        self.commandManager = None
        self.registerCommandManager(self.commandManager)
        self.registerDataManager(self.dataManager)
        self.registerEventManager(self.eventManager)


        # TODO: decouple the TCP handling of this proxy. Might have other types of connections, like LoRa.
        self.sources = {}
        self.newSources = {}
        self.connections = {}
        self.interfaces = {}
        self.lock = threading.RLock()
        self.sourceID = 0
        self.lastPktId = 0
        self.lastSourceID = 0
        self.conQueue = queue.Queue()  # queue of new connection requests
        self.recvQueue = queue.Queue()  # queue of incoming packets.

        self.ListenerThread = None
        self.ListenerLock = False

        for interfaceConstructor in interfaces:
            # make network interfaces.
            interfaceInst = self.makeInterface(interfaceConstructor)
            self.addInterface(interfaceInst)

        # # JOINING
        # self.joinAddress = (joinIP, joinPort)
        # if joinIP and joinPort:
        #     self.joinTCPNetwork(joinIP, joinPort)
        #
        #
        # # Thread starter
        # if listenerIP or loRaListener:
        #     self.ListenerThread = threading.Thread(target=self.listenerPopper)
        #     self.ListenerThread.start()
        # self.packetGrabber = threading.Thread(target=self.handleConnectionPackets)
        # self.packetGrabber.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()
        del self

    def start(self):
        self.startListening()
        # self.packetGrabber.start()
        Destination.start(self)

    def startListening(self):
        for interfaceName, interface in self.interfaces.items():
            interface.start()

    def closeAll(self):
        """ closes all connections """
        for interfaceName, interface in self.interfaces.items():
            interface.close()
            interface.end()
        for con in self.connections.values():
            con['connection'].close()

    def end(self):
        """ Terminates all threads """
        Destination.end(self)
        self.terminate = True
        self.closeAll()

    def registerCommandManager(self, commandManager):
        if cu.isCommandManager(commandManager):
            self.commandManager = commandManager
            commandManager.registerProxy(self)
            self.localSources.add(commandManager.getName())

    def registerDataManager(self, dataManager):
        if cu.isDataManager(dataManager):
            self.dataManager = dataManager
            dataManager.registerProxy(self)
            self.localSources.add(dataManager.getName())
            self.subscriptions[dataManager.getName()] = dataManager.getSubRecords()

    def registerEventManager(self, eventManager):
        if cu.isEventManager(eventManager):
            self.eventManager = eventManager
            eventManager.registerProxy(self)
            self.localSources.add(eventManager.getName())
            self.subscriptions[eventManager.getName()] = eventManager.getSubRecords()

    def makeInterface(self, factKWs):
        try:
            factKWs['proxyName'] = self.name
            l = lf.makeInterface(**factKWs)
            return l
        except lf.CreationException:
            msg = f'Proxy {self.name} could not create listener from supplied keyword arguments below: \n\n'
            for kw, arg in factKWs.items():
                msg += f'{kw}:  {arg}  \n'
            logging.error(msg)
            return None

    def addInterface(self, interface):
        # todo: implement this set proxy method and setQueues method. Once the definition of what the queues do is made of course...
        # interface.setProxy(self)
        # interface.setQueues(self.conQueue, self.recvQueue)
        self.interfaces[interface.name] = interface
        pass


    def handlePackage(self, package):
        """
        Will decide which connection to send package to, possibly based on a destination name in the package?
        :param package: Package object
        :return:
        """
        dest = self.subscriptions.get(package.source)
        if dest:
            self.sendPackageToSource(package, package.source, dest)

    def getSourceNameFromID(self, sourceID):
        """
        searches sources dictionary. Returns name based on sourceID
        :param sourceID: a number
        :return: sourceName string
        """
        for key, value in self.sources.items():
            if value['sourceID'] == sourceID:
                return key
        return None

    def getSourceIDFromName(self, sourceName):
        source = self.sources.get(sourceName)
        if source:
            source = source.get("sourceID")
            if source:
                return source
        raise SourceNotRegistered

    def getConnectionFromName(self, sourceName):
        """ a method that returns the remote connection to another proxy instance on another network.



        :param sourceName:
        :return:
        """
        try:
            conName = self.sources[sourceName]['connection']
            if self.networkConnection and self.networkConnection.conName == conName:
                return self.networkConnection
            for key, val in self.connections.items():
                if key == conName:
                    return val['connection']
        except:
            logging.exception("Error: cannot find connection")
        return None

    def listenerPopper(self):
        """
        threaded loop. Pops new connections off self.conQueue and registers connection + sends sourceName/sourceID mapping to the new connection
        connection = connection object (TCPserver or LoRa server objects)
        conProxyName = uniqueName of proxy object that connected. Used as key in connections dictionary
        address is (ip, port) or LoRa frequency
        """
        # TODO: add rejection if improper data is received
        while not self.terminate:
            # get the connection, blocking until something puts a connection on the queue.
            connection, conProxyName = self.conQueue.get()
            self.addConnection(connection, conProxyName)
            # Send existing network Sources to new connection
            bSources = pickle.dumps(self.getSourceMap())
            header = ph.defaultHeader(sourceID=0, packetID=self.getPktID(),
                                      channelType=ph.CONV_CHANNEL_TYPE[ChannelType.ProxyCommand],
                                      packetType=ph.PacketTypes.newSourceMap.value)
            bHeader = ph.dictToBytes(header)
            self.sendPacket(bHeader + bSources, connection)

    def addConnection(self, connection, conProxyName):
        # TODO: make this accessing of the connections dictionary thread safe.
        if self.connections.get(conProxyName):
            self.connections[conProxyName]['connection'] = connection
            self.connections[conProxyName]['conType'] = type(connection)
            self.connections[conProxyName]['conStatus'] = connection.getStatus()
        else:
            self.connections[conProxyName] = {
                'connection': connection,
                'conType': type(connection),
                'subscribedSources': [],
                'conStatus': connection.getStatus()
            }
        pass

    def joinNetwork(self, interfaceName, address):
        try:
            interface = self.interfaces[interfaceName]
            return interface.joinNetwork(address)
        except Exception as e:
            logging.error(f'Proxy {self.name} could not join destination network at address {address} through interface {interfaceName}'
            f' due to the following error: {e}')
            return False

    def assignSourceIDs(self, sources):
        """
        Only used by network boss.
        :param sources: list of sourceNames
        :return: dictionary of sourceNames keyed to integer sourceIDs
        """
        with self.lock:
            ret = {}
            # IDs = [i['sourceID'] for i in self.sources]
            # IDs.sort()
            # latestID = IDs[-1]
            # TODO: check all sources, proxy and local, and get the latest ID#
            # temporary, delete when you do that ^^^
            for sourceName in sources:
                self.lastSourceID += 1
                ret[sourceName] = self.lastSourceID
            return ret

    def registerSourcesLocallyFromNetwork(self, sources, connectionName):  # from children
        """
        :param sources: list of sourceNames
        :param connection: connection name (in self.connections keys) they came from
        :return:
        """
        for sourceName in sources:
            # assign source ID's
            if not self.sources.get(sourceName):
                self.newSources[sourceName] = {  # queue the new sources up in a temporary dictionary to be added once assigned IDs
                    'sourceID': None,
                    'connection': connectionName,
                    'metadata': {},
                    'fmt': ''
                }

    def registerLocalSourcesLocally(self, sources):
        """ registers location of sources"""
        for sourceName in sources:
            self.localSources.add(sourceName)
            self.sources[sourceName] = {
                'sourceID': None,
                'connection': None,
                'metadata': {},
                'fmt': ''
            }
        sourceIDs = self.assignSourceIDs(sources)
        self.updateSourceMap(sourceIDs)
        if self.commandManager:
            pass  # self.commandManager.registerProxySources()
        if self.eventManager:
            pass  # self.eventManager.registerProxySources()
        if self.dataManager:
            pass  # self.dataManager.registerProxySources()

    def updateSourceMap(self, sources: dict):
        """
        registers sources from the network to local self.sources dictionary

        If this runs before NetworkManager has been initialized, it will break

        :param sources: dictionary containing sourceName Keys with sourceID values
        :return:
        """
        for sourceName, sourceID in sources.items():
            # assign source ID's to sources that registered with me
            if sourceName == self.name:
                self.sourceID = sourceID

            #3 cases following, previously registered, currently from beneath but not yet assigned initial ID, or not registered
            if self.sources.get(sourceName): # Source already registered. New sourceID
                self.sources[sourceName]['sourceID'] = sourceID
            elif self.newSources.get(sourceName):  # source in registration process. Not ready until sourceID assigned (do that now)
                self.newSources[sourceName]['sourceID'] = sourceID
                self.sources[sourceName] = dict(self.newSources[sourceName])
                del self.newSources[sourceName]
            elif self.networkConnection is not None:  # Source not registered here, must come from network, register from network
                self.sources[sourceName] = {
                    'sourceID': sourceID,
                    'connection': self.networkConnection.conName,
                    'metadata': {},
                    'fmt': ''
                }
            else:
                raise "unknown source of source "+sourceName

    def registerSourcesWithNetwork(self, sources):
        """
        SOURCES MUST BE ALREADY REGISTERED LOCALLY

        registers sources with the network

        sends list up the chain to network boss who assigns IDs and sends them back down to all

        called with local sources

        :param sources: list of sources
        :return: None
        """
        if self.networkConnection:
            bSources = pickle.dumps(sources)
            header = ph.defaultHeader(sourceID=0, packetID=self.getPktID(),
                                      channelType=ph.CONV_CHANNEL_TYPE[ChannelType.ProxyCommand],
                                      packetType=ph.PacketTypes.registerNewSources.value)
            bHeader = ph.dictToBytes(header)
            self.sendPacket(bHeader + bSources, self.networkConnection)
        else:
            self._registerNewSources(None, None, None, sources)

    def removeSourcesFromNetwork(self, sources, connections):
        bSources = pickle.dumps(sources)
        header = ph.defaultHeader(sourceID=0, packetID=self.getPktID(),
                                  channelType=ph.CONV_CHANNEL_TYPE[ChannelType.ProxyCommand],
                                  packetType=ph.PacketTypes.removeSources.value)
        bHeader = ph.dictToBytes(header)
        for con in connections:
            self.sendPacket(bHeader + bSources, con)

    def sendPackageToSource(self, package: Package, sourceName, destinationName):
        """
        TODO: What if package.payload is not a dictionary?

        :param destinationName: sourceName in self.sources
        :param package: Package object
        :return: True/False if package sent
        """
        try:
            # print('sendPackageToSource', self.name, 'to', destinationName, package.channelType)
            # print(self.sources, self.connections)
            networkManager = self.getConnectionFromName(destinationName)
            # con is the actual connetion object (socket/loRa radio device) responsible for sending data to/from the remote proxy.
            destinationID = self.sources[destinationName]['sourceID']

            retries = PACKAGE_SEND_RETRIES
            sent = False
            while not sent and retries < PACKAGE_NUM_RETRIES:
                sent = networkManager.sendPackageTo(package, destinationName)
                retries = retries - 1
            if not sent:
                # handle the case where the package isn't sent
                logging.error(f'Proxy named {self.name} could not send package to destination named {destinationName}'
                              f'over network connection {networkManager}. ')
                return False
            else:
                # handle the case where the package is sent.
                return True


            # TODO: This metadata/data handling/translating should be handled by the interface not the proxy.
            md, fmt = ps.makeMetadataPayloadFmt(ps.sortedPayload(package.payload))
            packets = []  # list of packets to send
            if md != self.sources[destinationName]['metadata']:  # does metadata need to be sent
                packet = ps.getMetadataPacketFromPackage(self.sources[sourceName]['sourceID'], destinationID,
                                                         self.getPktID(), package, metadata=md, fmt=fmt)
                packets.append(packet)
                self.sources[destinationName]['metadata'] = md
                self.sources[destinationName]['fmt'] = fmt
            packetType = 0  # default to Data
            for value in package.payload.values():
                if type(value) not in (str, float, int, bool, type(None)) and not isinstance(value, Enum):
                    # packetType is set to 2 if package has complicated data structures. Tells proxy to just pickle it, otherwise it's 0
                    packetType = 2
            packet = ps.getPacketFromPackage(self.sources[sourceName]['sourceID'], destinationID, self.getPktID(),
                                             package, packetType, fmt)
            packets.append(packet)
            return networkManager.send(packets)
        except Exception as msg:
            logging.warning('Cannot Send Package to ' + destinationName + ", pkg=" + str(package.payload) + '\nmsg=' + str(msg))

    def sendPacketToSource(self, packet, source):
        destName = "NONE"
        try:
            if type(source) == str:
                destName = source
                destID = self.sources.get(source).get('sourceID')
            else:
                destID = source
                destName = self.getSourceNameFromID(destID)

            ph.setValue(packet, 'destinationID', destID)
            con = self.getConnectionFromName(destName)
            con.send(packet)
        except:
            logging.error(self.name + "could not send to source" + destName)

    def sendPacket(self, packet, connection):
        """ sends packet (bytes or bytearray) to connection"""
        connection.send(packet)

    # Moved to Network Manager.
    # def handleConnectionPackets(self):
    #     """
    #     Pops packets received from connections,
    #     converts to a payload,
    #     handles that payload
    #     :return:
    #     """
    #     while not self.terminate:
    #         if self.ListenerLock:
    #             time.sleep(1)
    #         elif self.recvQueue.qsize() > 0:
    #             try:
    #                 connectionName, packet = self.recvQueue.get()
    #                 packetType = ph.getValue(packet, "packetType")
    #                 sourceID = ph.getValue(packet, 'sourceID')
    #                 # sourceName = self.getSourceNameFromID(sourceID)
    #                 # print(self.name, "received packet from", connectionName, "of type", ph.getPacketTypeByID(packetType))
    #                 if packetType in (ph.PacketTypes.data.value, packetType == ph.PacketTypes.metadata.value,
    #                                   ph.PacketTypes.pickleData.value):
    #                     destID = ph.getValue(packet, 'destinationID')
    #                     destName = self.getSourceNameFromID(destID)
    #                     if destName:
    #                         source = self.sources.get(destName)
    #                         if destName not in self.localSources:
    #                             self.sendPacketToSource(packet, destName)
    #                         # if source.get('connection') is not None:
    #                         #     self.sendPacketToSource(packet, destName) # pass on
    #                         else:
    #                             head, payload = ps.getPayloadFromPacket(packet, self.sources)
    #                             _PACKET_METHODS[head['packetType']](self, connectionName, packet, head, payload)
    #                     else:
    #                         raise Exception("destinationID", destID, "not registered")
    #                 else:
    #                     head, payload = ps.getPayloadFromPacket(packet, self.sources)
    #                     _PACKET_METHODS[head['packetType']](self, connectionName, packet, head, payload)
    #             except SourceNotRegistered:
    #                 logging.error("Error: Source not registered")

    def _anyData(self, connection, packet, head, payload):
        """handles packetType data or pickleData """
        package = Package(source=self.getSourceNameFromID(head['sourceID']), payload=payload,
                          channelType=ph.getChannelTypeByValue(head['channelType']))
        ct = package.channelType
        logging.info(self.name + " RECEIVED DATA => " + str(dict(payload)))
        if ct == ChannelType.Data and self.dataManager:
            self.dataManager.accept(package)
        if ct == ChannelType.Event and self.eventManager:
            self.eventManager.accept(package)
        if ct == ChannelType.Command and self.commandManager:
            self.commandManager.accept(package)

    def _metadata(self, connection, packet, head, payload):
        """ handles Metadata payloads"""
        try:
            logging.info(self.name + ' received metadata ' + str(payload))
            source = self.sources[self.getSourceNameFromID(head['sourceID'])]
            md = ps.sortedPayload(payload)
            fmt = ps.getFmtFromMetadata(md)
            source['metadata'] = md
            source['fmt'] = fmt
        except KeyError:
            logging.warning(self.name + " Received payload for an unregistered source " + str(head['sourceID']) + ", "
                            + str(self.getSourceNameFromID(head['sourceID'])))
        except Exception as msg:
            logging.warning(self.name + ' metadata error: ' + str(msg))

    def _newSourceMap(self, connection, packet, head, payload):
        """ handles new sourceMapping payloads. Updates local sources dictionary and passes down to child connections"""
        self.updateSourceMap(payload)
        for con in self.connections.values():
            self.sendPacket(packet, con['connection'])

    def _registerNewSources(self, connectionName, packet, head, payload):
        """
        Receive a payload with new sources to register. 2 cases:
        1: Not network boss.
            register sources with their connection and pass source list to boss
        2: Network boss:
            register sources with connection, assign IDs, pass new sourceMap additions down to all connections
        :return:
        """
        self.registerSourcesLocallyFromNetwork(payload, connectionName)
        if self.networkConnection:  # pass request on up
            self.sendPacket(packet, self.networkConnection)
        else:  # assign ID's and pass them back down
            newSourceIDs = self.assignSourceIDs(payload)
            self.updateSourceMap(newSourceIDs)
            bData = pickle.dumps(newSourceIDs)

            # error, dictionary changed size while iterating? why? how to fix?
            for con in list(self.connections.values()):
                bHeader = ph.dictToBytes(ph.defaultHeader(packetType=ph.PacketTypes.newSourceMap.value,
                                                          channelType=ph.CONV_CHANNEL_TYPE[ChannelType.ProxyResponse],
                                                          packetSize=len(bData)))
                self.sendPacket(bHeader + bData, con['connection'])

    def _removeSources(self, connectionName, packet, head, payload):
        """not quite ready yet"""
        for source in payload:
            try:
                self.sources.pop(source)
            except:
                pass
        cons = [con['connection'] for con in self.connections.values()]  # get connection object from self.connections
        try:
            cons.remove(self.connections.get(connectionName)['connection'])  # attempt to remove the connection this was received from
        except:
            pass #  i can't imagine this failing
        if self.networkConnection and self.networkConnection.conName is not connectionName:
            cons.append(self.networkConnection)
        self.removeSourcesFromNetwork(payload, cons)

    def _conStatus(self, connectionName, packet, head, payload):
        currentStatus = self.connections[connectionName].connected
        if not currentStatus:
            msg = "Regained Connection to: "+connectionName
            try:
                conEvent = Events.EventPayload(source=self.name, eventType=Events.EventTypes.Connected, msg=msg)
                conPkg = Package(self.name, payload=conEvent, channelType=ChannelType.Event)
                self.eventManager.accept(conPkg)
            except Exception as e:
                logging.error(f'Proxy {self.name} tried to emit connection event with message {msg} but failed due to'
                              f'error {e}')

    def getPktID(self):
        self.lastPktId += 1
        return self.lastPktId

    def getSourceMap(self):
        """ :returns: Dictionary with sourceNames keyed to sourceIDs"""
        sourceMap = {}
        for sourceName, source in self.sources.items():
            sourceMap[sourceName] = source['sourceID']
        return sourceMap



    def addEventSubscription(self, eventManager, objName, namespace, publisher, events):
        # TODO: add the source to the global mapping, setting the destination object to eventManager.
        # See EventManager.subscribe for a template on how to do this.
        pass

    def addDataSubscription(self, dataManager, objName, namespace, publisher):
        subNamespace = self.subscriptions.get(namespace)
        if subNamespace is None:
            self.subscriptions[namespace] = []
        self.subscriptions[namespace].append((dataManager, objName, publisher))
        # print("just added", self.subscriptions)
        pass

    def addCommandSubscription(self, commandManager, objName, namespace):
        pass

    def getEventSubscriptions(self):
        # TODO: return all the subscriptions from other proxy objects.
        pass

    def getDataSubscriptions(self):
        pass

    def getCommandSubscriptions(self):
        pass

    def registerSubscriptionsFromNetwork(self, sourceNames):
        self.connections['subscribedSources'] += sourceNames

    def registerSubscriptionsWithNetwork(self, sourceNames):
        head = ph.defaultHeader(packetType=ph.PacketTypes.subscribe, sourceID=self.sourceID, channelType=ChannelType.ProxyCommand)
        packet = ph.dictToBytes(head)+pickle.dumps(sourceNames)
        for con in self.connections.keys():
            self.sendPacket(packet, con)
        if self.networkConnection:
            self.sendPacket(packet, self.networkConnection)


_PACKET_METHODS = {
    ph.PacketTypes.data.value: ProxyController._anyData,
    ph.PacketTypes.metadata.value: ProxyController._metadata,
    ph.PacketTypes.pickleData.value: ProxyController._anyData,
    ph.PacketTypes.newSourceMap.value: ProxyController._newSourceMap,
    ph.PacketTypes.registerNewSources.value: ProxyController._registerNewSources,
    ph.PacketTypes.removeSources.value: ProxyController._removeSources,
    ph.PacketTypes.conStatus.value: ProxyController._conStatus
}