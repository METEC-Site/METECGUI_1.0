import logging
from abc import ABC, abstractmethod

from Applications.TimsVan.Communication import ProxySerializer as ps, SimplifiedProxyHeader as ph


class NetworkConnection(ABC):
    def __init__(self, proxyName, conName, maxBytes=4096, namespace=None):
        # self.name = name  # generally fromProxyName_toProxyName (ex. pc1_pc2)
        self.proxyName = proxyName  # name of proxy this connector created by
        self.conName = conName  # name of proxy this connector is connected to through network
        self.maxBytes = maxBytes
        self.namespace = namespace
        self.terminate = False
        self.connected = False

    def send(self, packet: list or set or tuple or bytes or bytearray):
        sentAll = True
        if type(packet) not in (list, set, tuple):
            packet = (packet,)
        for singlePacket in packet:  # send all packets in a group (list, set, tuple)
            if type(singlePacket) in (bytes, bytearray):
                if len(packet[ph.HEADER_SIZE:]) > self.maxBytes:  #split packets if packet length > maxBytes
                    splitPackets = ps.splitPackets(singlePacket, self.maxBytes)
                    for partialPacket in splitPackets:
                        self._sendSinglePacket(partialPacket)
                else:
                    self._sendSinglePacket(singlePacket)
            else:
                sentAll = False
                logging.info("Send data was not proper type, should be bytes, bytearray, or list/set/tuple of bytes or bytearray, was "+str(type(singlePacket)))
        return sentAll

    @abstractmethod
    def _sendSinglePacket(self, packet):
        """
        send 1 packet guaranteed to be bytes with length < maxBytes
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def _recv(self):
        raise NotImplementedError

    @abstractmethod
    def getStatus(self):
        """ :returns status of network (True or False)"""
        raise NotImplementedError

    @abstractmethod
    def rejoin(self):
        """ rejoin network based on init information """
        raise NotImplementedError

    @abstractmethod
    def close(self):
        """ Closes connection"""
        raise NotImplementedError

    @abstractmethod
    def end(self):
        """ Closes connection and terminates any threads"""
        raise NotImplementedError
