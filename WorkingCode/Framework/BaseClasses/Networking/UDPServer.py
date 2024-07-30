import socket
import socketserver


class ThreadedHandler(socketserver.BaseRequestHandler):
    def handle(self):
        i=-10
        pass

class CustomThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    def __init__(self, IP_PORT, RequestHandlerClass):
        # Port scan will attempt to find an open port if set to True.
        s = socket.socket(type=socket.SOCK_DGRAM)
        e = s.connect_ex(IP_PORT)
        s.close()
        if e == 0:
            self.IP_PORT = IP_PORT
        else:
            self.IP_PORT = findFreePort(IP_PORT)
        socketserver.UDPServer.__init__(self, self.IP_PORT, RequestHandlerClass)
        socketserver.ThreadingMixIn.__init__(self)

def findFreePort(IP_PORT):
    # Shortcoming: Rare cases, when return the 'open' port and the OS assigns that port to another process is not accounted for.
    IP = IP_PORT[0]
    s=socket.socket()
    s.bind(('', 0))
    port =s.getsockname()[1]
    s.close()
    return (IP, port)