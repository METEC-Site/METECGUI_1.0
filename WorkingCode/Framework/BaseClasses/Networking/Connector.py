import logging
import threading
import time
from abc import ABC, abstractmethod

from Applications.TimsVan.Communication import ProxySerializer as ps, SimplifiedProxyHeader as ph


class Connector(ABC, threading.Thread):
    def __init__(self, name, conName, recvQueue, maxBytes=4096):
        threading.Thread.__init__(self)
        self.name = name  # generally fromProxyName_toProxyName (ex. pc1_pc2)
        self.conName=conName  # name of proxy this connector is connected to
        self.maxBytes = maxBytes
        self.terminate = False
        self.connected = False
        self.recvQueue = recvQueue

    def waitForConnection(self):
        while not self.connected:
            time.sleep(1)

    def start(self):
        threading.Thread.start(self)

    def send(self, packet: list or set or tuple or bytes or bytearray):
        sentAll = True
        if type(packet) not in (list, set, tuple):
            packet = (packet,)
        for singlePacket in packet:
            if type(singlePacket) in (bytes, bytearray):
                if len(packet[ph.HEADER_SIZE:]) > self.maxBytes:
                    splitPackets = ps.splitPackets(singlePacket, self.maxBytes)
                    for partialPacket in splitPackets:
                        self._send(partialPacket)
                else:
                    self._send(singlePacket)
            else:
                sentAll = False
                logging.info("Send data was not proper type, should be bytes, bytearray, or list/set/tuple of bytes or bytearray, was "+str(type(singlePacket)))
        return sentAll

    @abstractmethod
    def _send(self, packet):
        """
        send 1 packet guaranteed to be bytes with length < maxBytes
        :return:
        """
        pass


    @abstractmethod
    def _recv(self):
        pass

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def getStatus(self):
        """ :returns status of network (True or False)"""
        pass

    @abstractmethod
    def rejoin(self):
        """ rejoin network based on init information """

    @abstractmethod
    def close(self):
        """ Closes connection"""
        pass

    @abstractmethod
    def end(self):
        """ Closes connection and terminates any threads"""
        pass
