import os
import sys
cmdFrameworkPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(cmdFrameworkPath)
import threading
import Framework.Proxy.ProxyHeader as ph
from Framework.BaseClasses.Networking.NetworkConnection import NetworkConnection
from Framework.Proxy import ProxySerializer as ps
import queue

_example_packets = {
    "packetID": {
        1: b'1102910924',
        2: b'1023012143'
    }
}

MAX_BYTES = 4096

class LoRaConnector(NetworkConnection):
    def __init__(self, name, conName, lora, recvQueue):  # lora is an Sx127x_LoRa Object
        NetworkConnection.__init__(self, name, conName, recvQueue, maxBytes=90)
        # connector has self.connected, self.maxBytes, and self.terminate
        # maxBytes is maximum data bytes to be sent after header (14 bytes)
        self.lora = lora
        self.connected = True
        self._sendQueue = queue.Queue()  # thread safe queue
        self.recvQueue = recvQueue
        self.packets = {}
        #stores received packages by packageID
        self.recvThread = None
        self.start()

    def run(self):
        """Runs in new thread on initialization"""
        print("starting", self.name)
        self.recvThread = threading.Thread(target=self._recv)
        self.recvThread.start()

    def _sendSinglePacket(self, packet):
        packet = ph.setValue(packet, 'packetSize', len(packet)-ph.HEADER_SIZE)
        try:
            pass
            #  self.lora.transmit(packet)
        except Exception as msg:
            print("cannot send:", self.name, ph.getValue(packet, 'packetType'), msg)

    def _recv(self):
        """ recvThread"""
        packet = None  # receive packet
        self._handlePacket(packet)


    def _handlePacket(self, packet):
        """stores partial packets and puts complete packet onto proxy queue"""
        head = ph.bytesToDict(packet)
        if not self.packets.get(head['packetID']):
            self.packets[head['packetID']] = {}
        self.packets[head['packetID']][head['packetNum']] = packet
        if head['totalPackets'] == len(self.packets[head['packetID']]):
            allPackets = list(self.packets[head['packetID']].values())
            allPackets.sort(key=lambda x: ph.getValue(x, 'packetNum'))  # sort in packetNum
            packet = ps.combinePackets(allPackets)
            self.recvQueue.put((self.conName, packet))
            del self.packets[head['packetID']]

    def close(self):
        self.connected = False

    def end(self):
        self.terminate = True  # ends recvThread
        self.close()


class NetworkManager:
    """
    tcp network joiner and listener

    todo: post tim, network management- map out whole network
    """
    def __init__(self, pcName, maxRetries=10, retryWaitSeconds=1):
        self.name=pcName+"_tcpManager"
        self.proxyControllerName = pcName
        self.listen = False
        self.terminate = False
        self.connected = False
        self.conQueue = None
        self.lora = None  # instantiate loRa listener?
        self.listenerThread = None
        self.maxRetries = maxRetries
        self.retryWait = retryWaitSeconds

    def startListener(self, freq, conQueue, recvQueue):
        """starts listener thread"""
        self.listen = True
        self.listenerThread = threading.Thread(target=self.listenForNewConnection, args=(freq, conQueue, recvQueue))
        self.listenerThread.start()

    #listener
    def listenForNewConnection(self, address, conQueue, recvQueue):
        """
        starts listener server.
        :param address: address
        :param conQueue: queue to put new connections
        :param recvQueue: queue for Server to put received Packets
        :return: None
        """
        print(self.name + " starting listen server on")

    def close(self):
        """closes listener server"""
        self.listen = False

    def end(self):
        """terminates listener thread and closes server"""
        self.close()
        self.terminate = True

    #joiner
    def requestToJoin(self, address, proxyName, recvQueue):
        """
        join on address
        :param address:
        :param proxyName:
        :param recvQueue:
        :return:
        """
        pass
