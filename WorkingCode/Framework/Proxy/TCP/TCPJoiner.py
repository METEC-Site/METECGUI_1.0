import logging
import socket
import time

from Framework.Proxy.TCP import TCPConnection

TCP_MAX_BYTES = 8192
MAX_SEND_RETRIES = 5
CONNECTION_TIMEOUT = 60

class FailedToConnect(Exception):
    pass


def getTCPNetworkConnection(proxyName, namespace, joinAddress, maxJoinRetries=10, retryWaitSeconds=10, maxSendRetries=10):
    """
    called by proxyController when reading config
    """
    newSock, conName = initConnection(proxyName, namespace, joinAddress, maxJoinRetries, retryWaitSeconds)
    if newSock is None:
        return None
    return TCPConnection.TCPConnection(proxyName, conName, newSock, maxSendRetries, namespace=namespace)

def getTCPNetworkSocket(proxyName, namespace, joinAddress, maxJoinRetries=10, retryWaitSeconds=10, maxSendRetries=10):
    newSock, conName = initConnection(proxyName, namespace, joinAddress, maxJoinRetries, retryWaitSeconds)
    return newSock

def initConnection(proxyName, namespace, joinAddress, maxJoinRetries=10, retryWaitSeconds=10):
    if type(joinAddress) == str:  # join address is string with format address:port
        joinAddress = getAddress(joinAddress)
    logging.info("starting join socket on " + str(joinAddress))
    newS = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    newS.settimeout(CONNECTION_TIMEOUT)
    while maxJoinRetries > 0:
        try:
            print("JOINING ON", joinAddress)
            maxJoinRetries-=1
            newS.connect(joinAddress)
            return newS, "None"
            ## AUTHENTICATE
            # newS.sendall(ps.makeHandshake(proxyName, namespace))
            # authenticated = False
            # while not authenticated:
            #     handshake = newS.recv(1024)
            #     if len(handshake) > 0:
            #         handshakeData = ps.decodeHandshakePacket(handshake)
            #         if handshakeData:
            #             return newS, handshakeData['proxyName']
            #         else:
            #             raise FailedToConnect
        except ConnectionRefusedError or ConnectionError or ConnectionAbortedError or FailedToConnect as e:
            logging.error("Connection Failed")
        except Exception as e:
            logging.error(f'{proxyName} could not connect to network address {joinAddress} due to exception: {e}')
            time.sleep(retryWaitSeconds)
        return None, "Failed"

def getAddress(address:str):
    addr, port = address.split(sep=":")
    return addr, int(port)

if __name__ == '__main__':
    con = getTCPNetworkConnection("test", "test1", "localhost:50000")
