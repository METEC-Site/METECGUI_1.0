import json
import logging
import queue
import socket as sock
import threading
import time

from Framework.BaseClasses.Networking.NetworkConnection import NetworkConnection
from Framework.Proxy import ProxySerializer as ps
from Framework.Proxy import SimplifiedProxyHeader as ph
from Framework.Proxy.TCP import TCPJoiner

MAX_NUM_RETRIES = 5
SOCKET_TIMEOUT = 1
TCP_MAX_BYTES = 8192
SEND_TIMEOUT = 1
RECV_TIMEOUT = 1

class TCPConnection(NetworkConnection):
    def __init__(self, proxyName, conName, socket, maxNumRetries = MAX_NUM_RETRIES, namespace=None):
        """

        A class to help manage a connection from an established socket. It will take packets from this connection and
        forward them to a recv queue to be parsed by the main proxy object.

        """
        NetworkConnection.__init__(self, proxyName, conName, maxBytes=TCP_MAX_BYTES, namespace=namespace)
        # connector has self.connected, self.maxBytes, and self.terminate
        self.name = proxyName + "_" + conName

        # allocate socket resources.
        self.socket:sock.socket = socket
        self.socket.settimeout(SOCKET_TIMEOUT)
        self.joinAddress = socket.getpeername()

        # maxNumRetries is the number of retries for sending packets.
        if maxNumRetries < 0:
            maxNumRetries = 0
        if maxNumRetries > MAX_NUM_RETRIES:
            maxNumRetries = MAX_NUM_RETRIES
        self.maxNumRetries = maxNumRetries
        self.sendTimeout = SEND_TIMEOUT

        self.outgoingPktID = 1
        self.unsentPackets = set()  # stores received packages by packageID
        self.receivedPackets = {}

        # Allocating Threading resources
        self.lock = threading.RLock()
        self._sendQueue = queue.Queue()  # thread safe queue for outgoing packets
        self._recvQueue = queue.Queue()  # Thread safe queue for incoming packets.
        self.recvThread = threading.Thread(target=self._recv, name="".join([self.name, '_recvThread']))
        self.sendThread = threading.Thread(target=self._send, name="".join([self.name, '_sendThread']))

    def start(self):
        self.sendThread.start()
        self.recvThread.start()
        pass

    def end(self):
        self.terminate = True  # ends recvThread and sendThread.
        self.close()

    def connect(self, destAddress):
        """ A method that connects the socket into a destination address. """
        # destAddress is a tuple of the (IP, port) for the destination server.
        numRetries = self.maxNumRetries
        connected = False
        while not connected and numRetries >= 0:
            self.socket.settimeout(SOCKET_TIMEOUT)
            try:
                self.socket.connect(destAddress)
                self.destAddress = destAddress
                connected = True
                return True
            except OSError as e:
                self.rejoin()
                logging.error(f'Couldn\'t connect to the socket at destination address {destAddress} due to error: {e}')
            except Exception as e:
                # likely something went wrong
                logging.error(f'Couldn\'t connect to the socket at destination address {destAddress} due to error: {e}')
                pass
            logging.error(
                f'Socket connection to destination address {destAddress} failed, trying again ... {numRetries} more time')
            numRetries -= 1


    def verifySend(self, packet):
        sent = False
        sendBegin = time.time()
        while time.time() - sendBegin < SEND_TIMEOUT:
            sent = packet in self.unsentPackets
            if sent:
                break
        return sent


    def send(self, packet):
        # This packet is expected to be the serialized packet as per proxySerializer. IE it has a header (ProxyHeader header) and payload.
        if not self.terminate:
            self.unsentPackets.add(packet)
            self._sendQueue.put(packet)
        else:
            logging.error(f'Cannot put packet on queue for the TCP interface {self.name} as the connection is closed.')
        return self.verifySend(packet)

    def getRecvQueue(self):
        return self._recvQueue

    def _send(self):
        while not self.terminate and self.socket:
            try:
                sendingPacket = self._sendQueue.get(timeout=SEND_TIMEOUT)
                sent = self._sendPackets(sendingPacket)
                if sent:
                    self.unsentPackets.remove(sendingPacket)
                return True
            except queue.Empty:
                # nothing in the queue, so nothing to be done.
                pass
            except Exception as e:
                logging.error(f'TCP interface {self.name} could not send packet due to exception {e}')
                return False


    def _sendPackets(self, packet: list or set or tuple or bytes or bytearray):
        """ A method to send a single packet or array of packets to the destination as specified by socket.

        These packets must be ALREADY ENCODED pacets (IE header + payload)

        """
        sentAll = True
        packetsToSend = []
        if type(packet) in (bytes, bytearray):
            packetsToSend = [packet]
        elif type(packet) in [list, set, tuple]:
            for singlePacket in packet:
                if type(singlePacket) in (bytes, bytearray):
                    if len(packet) > self.maxBytes:
                        splitPackets = ps.splitPackets(singlePacket, self.maxBytes)
                        packetsToSend = [*packetsToSend, *splitPackets]
                else:
                    logging.error(f'{self.name} unable to send data; expecting data to be of type bytes or bytearray or a list of bytes or bytearrays. Instead got {type(packet)}')
                    return False
        for singlePacket in packetsToSend:
            sent = False
            numRetries = self.maxNumRetries
            while not sent and numRetries >= 0:
                sent = self._sendSinglePacket(singlePacket)
            if not sent:
                logging.error(f'Couldn\'t send one or all of packets in {packet} to destination {self.socket.getpeername()}')
                sentAll = False
                break
        return sentAll

    def _sendSinglePacket(self, packet):
        """ A method that sends ALREADY ENCODED/SERIALIZED packets (IE header+serialized bytes) to the destination specified by the socket.

        :param packet:
        :return:
        """
        # Overwriting the base class method of _send. _send is called by the base class send method.
        try:
            self.socket.sendall(packet)
            return True
        except OSError:  # this socket lost is closed
            # self.socket.connect(self.clientAddress)
            self.connect(self.destAddress)
        except BrokenPipeError:  # other socket is closed
            pass
        except Exception as msg:
            logging.error(f'{self.name} cannot send packet to destination {self.socket.getpeername()} due to error {msg}')
        return False

    def _recv(self):
        """Target of the receive thread. Will run until termination is set to True.

        This method will receive bytes off of the socket, the size of ProxyHeader Header Size. If the bytes are a header,
        then the rest of the payload can be received in accordance to the length described by the header.

        Will receive information from one and only one socket, the self socket."""
        while not self.terminate and self.socket:
            try:
                pBytes = self.socket.recv(4096)  # size header
                if len(pBytes) > 0:
                    # logging.debug(self.name+" received bytes "+str(pBytes))
                    firstPacketIndex = pBytes.index(b'\n')
                    if not firstPacketIndex:
                        logging.warning("Invalid packet received: "+str(pBytes))
                    while firstPacketIndex:
                        pDict = json.loads(pBytes[:firstPacketIndex])
                        self._recvQueue.put(pDict)
                        firstPacketIndex = pBytes.index(b'\n')
            except OSError as e:
                pass
                # timed out
                # self.end()
            except Exception as e:
                # logging.warning("Error in recv for " + self.name)
                pass

    def _recvData(self, bufferSize):
        bData = b''
        remainingLength = bufferSize
        while len(bData) < bufferSize:  # wait until received full length of packet
            moreData = self.socket.recv(remainingLength)
            bData = bData + moreData
            remainingLength = bufferSize - len(bData)
        return bData

    def _handleIncomingPacket(self, packet):
        """
        Some assumptions made when handling all these packages:
        1) the packets all agree on the total packet number sent.
            - Will have to ensure that the packets, when split, all agree.
        2) No packets have an incorrect packetID number.
            - This will
        3) The packet headers are all in the correct format.
            - Can mitigate errors with correct sending methods (TCP should handle) as well as a good checksum.
        4) No later messages share packet ID's
            - What to do and how to handle rollovers? Clean up received packets?

        :param packet:
        :return: A WHOLE Packet
        """
        pktID = ph.PacketAccess.getPacketID(packet)
        pktNum = ph.PacketAccess.getPacketNum(packet)
        totalPkts = ph.PacketAccess.getTotalPackets(packet)
        if totalPkts == 1:
            return packet

        if not self.receivedPackets.get(pktID):
            self.receivedPackets[pktID] = {pktID: packet}
        else:
            self.receivedPackets[pktID][pktID] = packet

        if len(self.receivedPackets[pktID]) == totalPkts:
            packets = self.receivedPackets.pop(pktID)
            orderedPackets = []
            for i in range(1, totalPkts+1):
                orderedPackets.append(packets[i])
            return ps.combinePackets(orderedPackets)

        if pktNum == totalPkts and len(self.receivedPackets[pktID]) != totalPkts:
            logging.warning(f"Missing packet number {pktNum} with packet ID {pktID}")


    def flushRecv(self):
        # TODO: Implement this method.
        pass


    def _isHeader(self, header):
        # TODO: add checks for correct header.
        if len(header) == ph.HEADER_SIZE:
            return True
        return False

    def getStatus(self):
        with self.lock:
            try:
                self.socket.getpeername()
                return True
            except Exception:
                return False

    def rejoin(self):
        self.socket:sock.socket = TCPJoiner.getTCPNetworkSocket(self.proxyName, self.namespace, self.joinAddress)

    def close(self):
        with self.lock:
            try:
                if self.connected:
                    self.socket.shutdown(sock.SHUT_RDWR)
                    self.socket.close()
                    self.connected = False
            except Exception as msg:
                logging.info(self.name + " Cannot close TCPconnection " + self.name + " due to following error: \n" + str(msg))