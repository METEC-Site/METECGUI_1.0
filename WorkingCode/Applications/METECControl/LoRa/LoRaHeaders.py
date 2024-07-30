from enum import Enum, auto

class HEADERS:
    Handshake = b'x00'
    Data = b'x01'
    Transmission = 'b'
    PayloadLength = 'h'
    PackageID = 'b'
    TransmissionID = 'h'

class HANDSHAKETYPE(Enum):
    Join = auto()
    Acknowledge = auto()
    Leave = auto()
    IDCheck = auto()
    Other = auto()
