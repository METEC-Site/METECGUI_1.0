import logging
import socket
import threading

from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Events import EventPayload, EventTypes
from Framework.BaseClasses.Package import Package

localhost = '127.0.0.1'
tcpPort = 11111
udpPort = 22222

class PortListener():
    def __init__(self, archiver, commandManager, dataManager, eventManager,
                 name='PenTestPortListener',
                 **kwargs):
        self.name = name
        self.archiver = archiver
        self.eventManager = eventManager
        self.eventManager.registerPublisher(self)

    def start(self):
        udpThread = threading.Thread(target=self.runUDP)
        tcpThread = threading.Thread(target=self.runTCP)
        udpThread.start()
        tcpThread.start()

    def runTCP(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((localhost, tcpPort))
            sock.listen()
            while True:
                conn, address = sock.accept()
                try:
                    with conn:
                        logging.info(f'Incoming connection from {address} on tcp port {localhost}:{tcpPort}')
                        data = conn.recv(1024)
                        msg = f'Incoming message {data} received from {address}.'
                        logging.info(msg)
                        evtPld = EventPayload(self.name, EventTypes.Default, msg=msg)
                        evtPkg = Package(self.name, payload=evtPld, channelType=ChannelType.Event)
                        self.eventManager.accept(evtPkg)
                        response = bytearray()
                        response.extend('Congratulations! You have found an easter egg!'.encode('utf-8'))
                        conn.sendall(response)
                except:
                    pass

    def runUDP(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((localhost, udpPort))
            while True:
                message, address = sock.recvfrom(1024)
                msg=f'Incoming message received from {address} on udp port {localhost}:{udpPort}'
                logging.info(msg)
                evtPld = EventPayload(self.name, EventTypes.Default, msg=msg)
                evtPkg = Package(self.name, payload=evtPld, channelType=ChannelType.Event)
                self.eventManager.accept(evtPkg)
                response = bytearray()
                response.extend('Congratulations! You have found an easter egg!'.encode('utf-8'))
                sock.sendto(response, address)