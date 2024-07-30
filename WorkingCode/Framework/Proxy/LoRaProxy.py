import json
import logging
import threading
from typing import Optional

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses.Commands import CommandMethod
from Framework.BaseClasses.Destination import Destination
from Framework.BaseClasses.Manager import Proxy_Base
from Framework.BaseClasses.Worker import Worker
from Framework.Manager.CommandManager import CommandManager
from Framework.Manager.DataManager import DataManager
from Framework.Manager.EventManager import EventManager
from Framework.Proxy import ProxySerializer as ps
from Framework.Proxy.TCP import TCPJoiner
from Utils import ClassUtils as cu


class SourceNotRegistered(Exception):
    pass


## DESTINATIONS
AIRMAR = "Airmar 2"
PROXY = "proxy"


# API
class ProxyController(Proxy_Base, Worker, Destination):
    """
    HAS:
     * list of subscriptions
        - maps single packet to any number of proxies and sources within those proxies so only 1 packet is sent
          through network for any number of destinations.
     * list of sources
        - List of all sources known by all proxies on network
     * NetworkInterface
        - Maps whole network regardless of type of connection (loRa or TCP)
        - maps sourceNames to their connections
        -

    Does:
     * Accepts packages with destinations from FRAMEWORK and sends to another FRAMEWORK
     * Maintains list of sources and subscriptions
     * receives packages from NetworkInterface and passes them to local objects within FRAMEWORk
    """

    def __init__(self,
                 archiver: Optional[DirectoryArchiver] = None,
                 commandManager: Optional[CommandManager] = None,
                 dataManager: Optional[DataManager] = None,
                 eventManager: Optional[EventManager] = None,
                 name: str = None,
                 proxyConnectionPath: str = None,
                 mappingPath: str = None):  # path to network configuration
        Destination.__init__(self, name)
        Worker.__init__(self, archiver, commandManager, dataManager, eventManager, name)
        # self.subscriptions = {}
        # self.localSources = set()
        self.connectionConfigPath = proxyConnectionPath
        # Register with Managers and ask for sources and subscriptions where applicable.
        # self.eventManager: EventManager = None
        # self.dataManager: DataManager = None
        # self.commandManager: CommandManager = None
        self.eventManager = eventManager
        self.dataManager = dataManager
        self.commandManager = commandManager
        self.registerCommandManager(self.commandManager)
        self.registerDataManager(self.dataManager)
        self.registerEventManager(self.eventManager)


        self.networkRadioID = None
        self.sourceMap = {}
        if mappingPath:
            self.sourceMap = self.readSourceConfig(mappingPath)
        self.networkRadioID = None
        for radioID, destination in self.sourceMap.items():
            if destination == PROXY:
                self.networkRadioID = radioID

        self.lock = threading.RLock()
        self.networkConnection = None

        self.packetGrabber = threading.Thread(target=self.handleConnectionPackets)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()
        del self

    def start(self):
        if self.connectionConfigPath:
            if self.startConnections(self.connectionConfigPath):
                self.packetGrabber.start()
        if not self.networkConnection:
            logging.warning("NO CONNECTION TO NETWORK ESTABLISHED")

    def registerCommandManager(self, commandManager):
        if cu.isCommandManager(commandManager):
            self.commandManager = commandManager
            commandManager.registerProxy(self)
            # self.localSources.add(commandManager.getName())

    def registerDataManager(self, dataManager):
        if cu.isDataManager(dataManager):
            self.dataManager = dataManager
            dataManager.registerProxy(self)
            self.localSources.add(dataManager.getName())
            # self.subscriptions[dataManager.getName()] = dataManager.getSubRecords()

    def registerEventManager(self, eventManager):
        if cu.isEventManager(eventManager):
            self.eventManager = eventManager
            eventManager.registerProxy(self)
            # self.localSources.add(eventManager.getName())
            # self.subscriptions[eventManager.getName()] = eventManager.getSubRecords()

    def startConnections(self, proxyConnectionJSON):
        # todo: load this in first as a json and config in __init__. Then do work with it
        with open(proxyConnectionJSON) as subs:
            reader = json.load(subs)
            if reader['NetworkConnection']['connector'] == 'tcp':
                self.networkConnection = TCPJoiner.getTCPNetworkConnection(self.name, self.namespace,
                                                                  reader['NetworkConnection']['address'],
                                                                  reader['NetworkConnection']["maxJoinRetries"],
                                                                  reader['NetworkConnection']['retryWaitSeconds'],
                                                                  reader['NetworkConnection']['maxSendRetries'])
                self.networkConnection.start()
                return self.networkConnection is not None
            elif reader['NetworkConnection']['connector'] == 'lora':
                pass  # None are LoRa as all NetworkConnections are through tcp to the RaspberryPi repeaters which host the tcp server
            return False


    def readSourceConfig(self, sourceConfigPath):
        try:
            sourceMap = {}
            with open(sourceConfigPath) as sourceConfigFile:
                sourceMapping:list = json.load(sourceConfigFile)
                for source in sourceMapping:
                    sourceMap[source['RadioID']] = source['Destination']
            return sourceMap
        except Exception as msg:
            logging.error(msg)
            raise Exception

    def handlePackage(self, package):
        """Handles incoming packages from the framework and sends them out over LoRa to the repeater."""
        self.sendPackageToLoRa(package)


    def sendPackageToLoRa(self, package):
        """ A method that serializes a framework package and sends it over a socket to a waiting TCP/LoRa repeater. """
        pktBytes = ps.makeRepeaterDicts(package, self.networkRadioID)# returns
        self.loraConnection.send(pktBytes)
        self.networkConnection.send(pktBytes)
        pass

    def getNetworkStatus(self):
        status = {}
        if self.networkConnection is not None:
            status[self.networkConnection.name] = self.networkConnection.getStatus()
            if not status[self.networkConnection.name]:
                self.networkConnection.rejoin()

        return status

    # def joinLoRaNetwork(self):
    #     raise NotImplementedError

    def sendBytes(self, packet):
        self.networkConnection.send(packet)

    @CommandMethod
    def handleConnectionPackets(self):
        """
        Pops packets received from connections,
        converts to a payload,
        handles that payload
        :return:
        """
        logging.info("PC: waiting for incoming packets")
        while not self.terminate:
            if self.networkConnection.getRecvQueue().qsize() > 0:
                try:
                    packet = self.networkConnection.getRecvQueue().get()
                    logging.info("PACKET "+str(packet))
                    package = ps.getRepeaterDict(packet)  # get Radio and payload dictionary from packet ( pickle loads or micro json )
                    radioID = package['RadioID']
                    payloadBytes = package['Payload']
                    dest = None
                    logging.debug(self.name + " received Packet" + packet)
                    for source in self.sourceMap:
                        if source['RadioID'] == radioID:
                            dest = source['Destination']
                    if dest == AIRMAR:
                        self.commandManager.createCommandPackage(self.name, "handleConnectionPackets", "Airmar 2", "print")
                    if dest == PROXY:
                        payload = ps.deserialize(payloadBytes)
                        # ct = ph.getChannelTypeByValue(ph.PacketAccess.getChannelType(payload))
                        # TODO: Get channel type somehow
                        # pkg = Package(source=name, payload=payload, channelType=ct, namespace=self.namespace)
                        # if ct == ChannelType.Command:
                        #     self.commandManager.accept(pkg)
                        # if ct == ChannelType.data:
                        #     self.dataManager.accept(pkg)
                        # if ct == ChannelType.Event:
                        #     self.eventManager.accept(pkg)
                except Exception as msg:
                    logging.warning(msg)


    def closeAll(self):
        """ closes all connections """
        if self.networkConnection:
            self.networkConnection.close()

    def end(self):
        """ Terminates all threads """
        Destination.end(self)
        self.closeAll()
        if self.networkConnection:
            self.networkConnection.end()