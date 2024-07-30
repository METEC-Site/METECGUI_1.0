import logging
import os
import pickle
import queue
import socket
import sys
import threading

from Framework.Proxy import SimplifiedProxyHeader as ph
from Framework.Proxy.TCP.TCPConnection import TCPConnection

cmdFrameworkPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(cmdFrameworkPath)
from Framework.Proxy.TCP.TCPListener import TCPListener

TCP_MAX_BYTES = 8192
CONN_GET_TIMEOUT = 1
CONNECTION_TIMEOUT = 1

CON_OBJECT = None

connections = {
    'connectionName':{
        'conObject': CON_OBJECT,
        'OBJECT_NAMES_ON_OTHER_SIDE': []
    }
}

class TCPNetworkManager:
    """
    tcp network joiner and listener

    todo: post tim, network management- map out whole network
    """
    def __init__(self, proxyNamespace, proxyName, interfaceName, listenAddress, maxRetries=10, retryWaitSeconds=1, listenTimeout= 5):
        self.proxyName = proxyName
        self.proxyNamespace = proxyNamespace
        self.name=interfaceName
        self.terminate = False
        self.connected = False
        self.conQueue = queue.Queue()
        self.recvQueue = queue.Queue()

        self.connections = set()

        listenerName = proxyName + '_tcpListener'
        self.listener = TCPListener(proxyName, listenerName, listenAddress, self.conQueue, maxRetries, retryWaitSeconds, listenTimeout)
        self.connectionThread = threading.Thread(target=self.handleNewConnections)

    def start(self):
        self.listen()
        self.connectionThread.start()

    def listen(self):
        """starts listener thread"""
        self.listener.start()

    def close(self):
        try:
            self.listener.close()
        except Exception:
            logging.info(f"Listener for TCPNetwork Manager {self.name} already closed")

    def end(self):
        """terminates listener thread and closes server"""
        self.close()
        self.terminate = True

    def decodeHandshake(self, handshake):
        # TODO: this handshake should be a package or dictionary of some kind, and should be serialized using serializer.
        handshake = pickle.loads(handshake)
        return handshake

    def makeHandshake(self):

        handshake = {
            'proxyNamespace': self.proxyNamespace,
            'proxyName': self.proxyName
        }
        serialized = pickle.dumps(handshake)
        packetType = 3 # packet Type 3 is for pickled data.
        header = ph.defaultHeader(packetType)
        completePacket = b''.join([header, serialized])
        return completePacket

    def sendPackageTo(self, package, destinationName):
        payloadBytearrays = self.encodePackage(package)
        destinationConnection = self.getConnectionFromName(destinationName)
        for payloadBytearray in payloadBytearrays:
            sent = destinationConnection.send(payloadBytearray)
        pass

    def receivePacket(self, fromConnection, packet):
        """ put onto package receive queue handler in proxy Interface """
        raise NotImplementedError

    # def joinNetwork(self, destinationAddress):
    #     """
    #
    #     Destination address is a tuple of (IP, port) of the listening port.
    #
    #     """
    #     interface = TCPInterface(self.proxyName, 'CONNECTION_NAME', destinationAddress, self.recvQueue)
    #     connected = interface.connect(destinationAddress)
    #     if not connected:
    #         logging.error(f'Network Manager {self.name} could not join network at destination address {destinationAddress}')
    #         return False
    #     handshake = self.makeHandshake(interface)
    #     # Interface should be started before send sends. Therefore, the recvQueue should loaded and passed before this
    #     # TODO: Here, interface needs to encode the handshake as the bytes/payload definition.
    #     interface.send(handshake)
    #     # after this is sent, a return handshake will be sent to the interface. Right now it will be interpreted and put onto the recv queue.
    #     # This recv queue will be managed by something, and this is where the handshake can be found.
    #     # TODO: handle stuff from the recv queue. WAIT::: _recv only starts AFTER the start method is called. Since this is new, we can receive with impunity.
    #     # TODO: ensure the destination is sending a response handshake properly.
    #
    #     retHandshake = interface.recvHandshake()
    #     decoded = self.decodeHandshake(retHandshake)
    #     connectionName = decoded['proxyName']
    #     connectionIP = decoded['IP']
    #     connectionPort = decoded['port']
    #     interface.setAddress((connectionIP, connectionPort))
    #     # DO SOMETHING with this information/connection to register with the other parts of the network.

    # this method goes hand in hand with the handleNewConnections. Calling this in one network manager will then cause a new connection in the other manager.
    def joinNetwork(self, networkAddress):
        try:
            newS = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            newS.settimeout(CONNECTION_TIMEOUT)
            newS.connect(networkAddress)
            newConnection = TCPConnection(self.proxyName, None, newS)
            self.connections.add(newConnection)
            # todo: add somehting here to connect with other network. Likely request information about its connections? Other networking?
            return True
        except Exception as e:
            logging.error(f'Could not connect to network address {networkAddress} due to exception {e}')
            return False

    def handleNewConnections(self):
        while not self.terminate:
            try:
                newConnection = self.conQueue.get(timeout=CONN_GET_TIMEOUT)
                self.connections.add(newConnection)

            except queue.Empty:
                pass
            except Exception as e:
                logging.error(f'Network Manager {self.name} could not add new network connection due to exception {e}')

    #
    # # joiner
    # # put this on something else...
    # def requestToJoin(self, ip, port, proxyName, recvQueue):
    #     """
    #     :param ip: ip to join
    #     :param port: port to join on
    #     :param proxyName: name of proxy that is joining the network
    #     :param recvQueue: queue for client socket to put received packets into
    #     :return: None
    #     """
    #     joinSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     joinConnected = False
    #     joinSocket.settimeout(5)
    #     maxRetries = self.maxRetries
    #     while not joinConnected and not self.terminate and maxRetries > 0:
    #         try:
    #             joinSocket.connect((ip, port))
    #             joinConnected = True
    #             handshake = self.makeHandshake()
    #             joinSocket.send(handshake)  # send unique proxy name
    #             returnHandshake = pickle.loads(joinSocket.recv(64))  # name of who it's connected to
    #             conName = self.decodeHandshake(returnHandshake)
    #             return TCPInterface(proxyName + "_" + conName, conName, joinSocket, recvQueue)
    #         except:
    #             maxRetries -= 1
    #             logging.warning(self.name + " requestToJoin failed... trying again in 1 second")
    #             time.sleep(1)
    #     logging.warning(self.name + f' max number of retries reached when trying to connect to {ip}:{port}')
    #     return False
    #

    # def handleConnectionPackets(self):
    #     """
    #     Pops packets received from connections,
    #     converts to a payload,
    #     handles that payload
    #     :return:
    #     """
    #     while not self.terminate:
    #
    #         try:
    #             connectionName, packet = self.recvQueue.get()
    #             packetType = ph.getValue(packet, "packetType")
    #             sourceID = ph.getValue(packet, 'sourceID')
    #
    #             if packetType in (ph.PacketTypes.data.value, packetType == ph.PacketTypes.metadata.value,
    #                               ph.PacketTypes.pickleData.value):
    #                 destID = ph.getValue(packet, 'destinationID')
    #                 destName = self.getSourceNameFromID(destID)
    #                 if destName:
    #                     source = self.sources.get(destName)
    #                     if destName not in self.localSources:
    #                         self.sendPacketToSource(packet, destName)
    #                     # if source.get('connection') is not None:
    #                     #     self.sendPacketToSource(packet, destName) # pass on
    #                     else:
    #                         head, payload = ps.getPayloadFromPacket(packet, self.sources)
    #                         _PACKET_METHODS[head['packetType']](self, connectionName, packet, head, payload)
    #                 else:
    #                     raise Exception("destinationID", destID, "not registered")
    #             else:
    #                 head, payload = ps.getPayloadFromPacket(packet, self.sources)
    #                 _PACKET_METHODS[head['packetType']](self, connectionName, packet, head, payload)
    #         except SourceNotRegistered:
    #             logging.error("Error: Source not registered")