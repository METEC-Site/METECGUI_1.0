import logging
import socket
import threading

from Framework.Proxy.TCP.TCPConnection import TCPConnection

TCP_MAX_BYTES = 8192

class TCPListener:
    """
    A class designed to listen for incoming requests to connect, and establish a connection once those requests come in.

    """
    def __init__(self, proxyName, listenerName, listenAddress, connectionQueue, maxRetries=10, retryWaitSeconds=1, listenTimeout=5):
        self.name = listenerName
        self.proxyName = proxyName
        self.conQueue = connectionQueue

        self.proxy = None
        self.listen = False

        self.listenAddress =listenAddress
        self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.maxRetries = int(maxRetries)
        self.retryWait = int(retryWaitSeconds)
        self.listenTimeout = int(listenTimeout)

    def start(self):
        """starts listener thread"""
        try:
            self.listen = True
            self.listenSocket.bind(self.listenAddress)
            self.listenerThread = threading.Thread(target=self.listenForNewConnection)
            self.listenerThread.start()
            return True
        except OSError:
            # something already bound to port.
            # todo: could not bind socket to IP/port. Will have to come up with another way to handle this, or report it.
            logging.error(f'Listener {self.name} could not bind to address {self.listenAddress}')
            return False
        except Exception as e:
            logging.error(f'Listener {self.name} could not start listening due to following exception: {e}')

    #listener
    def listenForNewConnection(self):
        """
        starts listener server.
        :param ip: listener server IP
        :param port: listener server Port
        :param conQueue: queue to put new connections
        :param recvQueue: queue for Server to put received Packets
        :return: None
        """
        logging.info(f'{self.name} starting server: listening on ({self.listenAddress})')
        self.listenSocket.listen(100) # maximum 100 connection requests in queue at a time.
        while self.listen:
            try:
                self.listenSocket.settimeout(self.listenTimeout)
                connSock, addr = self.listenSocket.accept()
                #TODO: need to make SURE this is a proxy connection and not some random or malicious connection
                #todo: handshake and approval before socket is put into connection object
                connection = TCPConnection(self.proxyName, None, connSock)
                connection.start()
                self.conQueue.put(connection)
            except socket.timeout:
                pass
            except Exception as msg:
                logging.warning(self.name+ ' Error listening for new connection: ' + str(msg))
        # logging.warning('Closing listener on', ip, port)

    def close(self):
        """closes listener server"""
        self.listen = False
        try:
            self.listenSocket.shutdown(socket.SHUT_RDWR)
            self.listenSocket.close()
        except Exception:
            logging.info("listener already closed")

    def end(self):
        """terminates listener thread and closes server"""
        self.close()
