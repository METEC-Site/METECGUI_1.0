import logging
import pickle
import queue
import socket
import threading

from Framework.Proxy import ProxySerializer as ps
# from Framework.Proxy.LoRa import
from Framework.Proxy import SimplifiedProxyHeader as ph
from Framework.Proxy.TCP import TCPListener, TCPConnection

TCP_MAX_BYTES = 8192
CONN_GET_TIMEOUT = 1
CONNECTION_TIMEOUT = 1

class NetworkInterface:
    """
     - Maps whole network regardless of type of connection (loRa or TCP)
     - maps sourceNames to their connections

    """
    def __init__(self, name, proxyName,
                 namespace=None,
                 tcpListenAddress:tuple=None, tcpJoinAddress:tuple=None,
                 loRaListener=None, loRaJoinAddress=None):
        self.name = name
        self.proxyName = proxyName
        self.namespace = namespace
        self.recvQueue = queue.Queue()
        self.lastPktId = 0
        self.lastSourceID = 0
        self.tcpListenAddress = tcpListenAddress
        self.tcpJoinAddress = tcpJoinAddress
        self.loRaListener = None
        self.loRaJoinAddress = None
        #connections
        self.networkConnection = None  # The connection to a network
        self.connections = {}  # connections to *THIS* network
        self.sources = {}

        self.conQueue = queue.Queue()  # All new connections pushed to this queue to be handled one at a time
        # setup listeners
        if self.tcpListenAddress and self.tcpJoinAddress:
            self.tcpListener = TCPListener.TCPListener(proxyName, proxyName+"_TCPListener", tcpListenAddress, self.conQueue)
        if self.loRaListener:
            # self.loRaListener = LoRaListener.LoRaListener(proxyName, proxyName+"_LoRaListener", loRaListener, self.conQueue)
            pass

        # JOINING
        if self.tcpJoinAddress:
            self.joinTCPNetwork(self.tcpJoinAddress)

        #lora
        if self.loRaJoinAddress:
            self.joinLoRaNetwork(self.loRaJoinAddress)

        #start threads
        if self.tcpListenAddress or self.loRaListener:
            self.connectionThread = threading.Thread(target=self._handleNewConnections)


    def start(self):
        self.listen()
        self.connectionThread.start()

    def listen(self):
        """starts listener thread"""
        if self.tcpListener:
            self.tcpListener.start()
        if self.loRaListener:
            self.loRaListener.start()

    def close(self):
        try:
            self.listener.close()
        except Exception:
            logging.info(f"Listener for TCPNetwork Manager {self.name} already closed")

    def end(self):
        """terminates listener thread and closes server"""
        self.close()
        self.terminate = True


    def sendPackageTo(self, package, destinationName):
        payloadBytearrays = self.encodePackage(package)
        destinationConnection = self.getConnectionFromName(destinationName)
        for payloadBytearray in payloadBytearrays:
            sent = destinationConnection.send(payloadBytearray)
        pass

    def encodePackage(self, package):
        # ps.getPacketFromPackage()
        raise NotImplementedError

    def receivePacket(self, fromConnection, packet):
        """ put onto package receive queue handler in proxy Interface """
        raise NotImplementedError

    def getStatus(self):
        """ Returns all known connection objects and their current connection status """
        raise NotImplementedError

    def _handleNewConnections(self):
        while not self.terminate:
            try:
                newConnection = self.conQueue.get(timeout=CONN_GET_TIMEOUT)
                self.registerConnection(newConnection, newConnection.conName)
                bSources = pickle.dumps(self.getSourceMap())
                header = ph.defaultHeader(sourceID=0, packetID=self.getPktID(),
                                          channelType=ph.CONV_CHANNEL_TYPE[ph.ChannelType.ProxyCommand],
                                          packetType=ph.PacketTypes.newSourceMap.value)
                bHeader = ph.dictToBytes(header)
                newConnection.send(bHeader+bSources)

            except queue.Empty:
                pass
            except Exception as e:
                logging.error(f'Network Manager {self.name} could not add new network connection due to exception {e}')

    def getConnectionFromName(self, sourceName):
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

    def registerConnection(self, connection, conProxyName):
        """ Used by _handleNewConnections"""
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

    def joinTCPNetwork(self, joinAddress):
        """
        Need to send handshake and get connection approval verification of some sort before adding connection
        """
        try:
            newS = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            newS.settimeout(CONNECTION_TIMEOUT)
            newS.connect(joinAddress)
            ## AUTHENTICATE
            newS.sendall(ps.makeHandshake(self.proxyName, self.namespace))
            authenticated = False
            while not authenticated:
                handshake = newS.recv(1024)
                if len(handshake) > 0:
                    handshakeData = ps.decodeHandshakePacket(handshake)
                    if handshakeData:
                        self.networkConnection = TCPConnection.TCPConnection(self.proxyName, None, newS, self.recvQueue)
                        # todo: add something here to connect with other network. Likely request information about its connections? Other networking?
                        return True
                    else:
                        return False

        except Exception as e:
            logging.error(f'{self.name} could not connect to network address {joinAddress} due to exception {e}')
            return False

    def joinLoRaNetwork(self, joinAddress):
        raise NotImplementedError

    def getPktID(self):
        self.lastPktId += 1
        return self.lastPktId

    def getSourceMap(self):
        """ :returns: Dictionary with sourceNames keyed to sourceIDs"""
        sourceMap = {}
        for sourceName, source in self.sources.items():
            sourceMap[sourceName] = source['sourceID']
        return sourceMap