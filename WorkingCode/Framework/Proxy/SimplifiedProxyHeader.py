import functools
import struct as s
from collections import OrderedDict

CHECKSUM_POLYNOMIAL = 1011


# class PacketTypes(Enum):
#     #Framework packets
#     data = 0  # regular ol' data. uses latest known metadata for source
#     pickleData = 2  # pickled Data and Metadata dict (if sending complex data
#
#     # Internal Network packets
#     metadata = 1   # pickled MD dict with data types
#     registerNewSources = 3  # pass list of new sources up network to be assigned IDs
#     newSourceMap = 4  # send new source ID's to be available to the network
#     requestJoin = 5  # send new source ID's to be available to the network
#     removeSources = 6  # remove sources from the network
#     conStatus = 7  # Check status of network
#     subscribe = 8  # subscription info packet
#     handshake = 9  # handshake authentication packets

# def getPacketTypeByID(value):
#     for t in PacketTypes:
#         if t.value == value:
#             return t.name

#
# # convert channel type to header value
# CONV_CHANNEL_TYPE = {
#     ChannelType.Data: 0,
#     ChannelType.Metadata: 1,
#     ChannelType.Config: 2,
#     ChannelType.DirConfig: 3,
#     ChannelType.Command: 4,
#     ChannelType.Response: 5,
#     ChannelType.Event: 6,
#     ChannelType.Index: 7,
#     ChannelType.Log: 8,
#     ChannelType.Other: 9,
#     ChannelType.Base: 10,
#     ChannelType.ProxyCommand: 11,
#     ChannelType.ProxyResponse: 12,
#     ChannelType.GUIInfo: 13,
#     ChannelType.InternalSignal: 14
# }
#
# def getChannelTypeByValue(val):
#     for ct, value in CONV_CHANNEL_TYPE.items():
#         if value == val:
#             return ct
#     return None

# PACKET_TYPE_KEY = 'packetType'
# SOURCE_ID_KEY = 'sourceID'
# DESTINATION_ID_KEY = 'destinationID'
# CHANNEL_TYPE_KEY = 'channelType'
PACKET_ID_KEY = 'packetID'
PACKET_NUM_KEY = 'packetNum'
TOTAL_PKT_KEY = 'totalPackets'
PAYLOAD_SIZE_KEY = 'payloadSize'
CHECKSUM_KEY = 'checksum'
DATA_KEY = 'data'

HEADER_FMT_DICT = OrderedDict({
    # PACKET_TYPE_KEY: {"fmt": "B", "offset": 0},
    # SOURCE_ID_KEY: {"fmt": "H", "offset": 1},
    # DESTINATION_ID_KEY: {"fmt": "H", "offset": 3},
    # CHANNEL_TYPE_KEY: {"fmt": "B", "offset": 11},
    PACKET_ID_KEY: {"fmt": "I", "offset": 0},
    PACKET_NUM_KEY: {"fmt": "B", "offset": 4},
    TOTAL_PKT_KEY: {"fmt": "B", "offset": 5},
    PAYLOAD_SIZE_KEY: {"fmt": "H", "offset": 6},  #only the size after the header (IE of this payload)
    CHECKSUM_KEY: {'fmt': "B", "offset": 8}, #checksum pf header only.
    DATA_KEY: {'fmt': None, 'offset': 9}
})

ENDIAN = '<'
HEADER_FMT = ENDIAN+'IBBHB'
HEADER_SIZE = s.calcsize(HEADER_FMT)  # 14 bytes

def newChecksum(func):
    @functools.wraps
    def newMethod(packet, value):
        packet = func(packet, value)
        newChecksum = calcChecksum(packet)
        packet = PacketAccess.setChecksum(packet, newChecksum)
        return packet

    return newMethod

class PacketAccess:
    # TODO: add additional checks for each of the header access. IE trying to input a number larger than the allowed size.
    # Note: all these setters act in place on the packet, but the packet is returned anyway for convenience.
    @staticmethod
    def getHeader(packet):
        header = packet[0:HEADER_SIZE]
        if not len(header) == HEADER_SIZE:
            raise IndexError(f'Could not unpack header from buffer, packet is too small (size {len(packet)}, need at least {HEADER_SIZE}')
        return header # header is the corresponding values of the fields.

    @newChecksum
    @staticmethod
    def setPayload(packet, data):
        header = PacketAccess.getHeader(packet)

        if not type(data) == bytes or type(data) is bytearray:
            raise TypeError(f'Expecting data to be of type bytearray or bytes, got type {type(data)} instead.')
            # todo: do something to mark this!! improperly serialized.
        else:
            dataLen = len(data)
            wholePacket = b''.join([header, data])
            wholePacket = PacketAccess.setPayloadSize(wholePacket, dataLen)
            return wholePacket
        pass

    @staticmethod
    def getPayload(packet):
        offset = HEADER_FMT_DICT[DATA_KEY]['offset']
        pld = packet[offset:]
        header = PacketAccess.getHeader(packet)
        hSize = PacketAccess.getPayloadSize(header)
        if not hSize == len(pld):
            # sizes don't match!!!
            pass
        else:
            return pld

    @staticmethod
    @newChecksum
    def setPacketID(packet):
        return getValue(packet, PACKET_ID_KEY)

    @staticmethod
    @newChecksum
    def setPacketID(packet, packetID):
        return setValue(packet, PACKET_ID_KEY, packetID)

    @staticmethod
    def getPacketNum(packet):
        return getValue(packet, PACKET_NUM_KEY)

    @staticmethod
    @newChecksum
    def setPacketNum(packet, num):
        return setValue(packet, PACKET_NUM_KEY, num)

    @staticmethod
    def getTotalPackets(packet):
        return getValue(packet, TOTAL_PKT_KEY)

    @staticmethod
    @newChecksum
    def setTotalPackets(packet, total):
        return setValue(packet, TOTAL_PKT_KEY, total)

    @staticmethod
    def getPayloadSize(packet):
        return getValue(packet, PAYLOAD_SIZE_KEY)

    @staticmethod
    @newChecksum
    def setPayloadSize(packet, size):
        return setValue(packet, PAYLOAD_SIZE_KEY, size)

    @staticmethod
    def getChecksum(packet):
        return getValue(packet, CHECKSUM_KEY)

    @staticmethod
    def setChecksum(packet, checksum):
        return setValue(packet, CHECKSUM_KEY, checksum)

# TODO: make checksum calc and checks
def calcChecksum(input):
    """ Based on the CRC (cycle redundancy check) Example found here:

    https://en.wikipedia.org/wiki/Cyclic_redundancy_check

    expecting an input in bytearray or bytes format. Input is to be the entire packet (header and payload included) and
    will be trimmed of the payload/existing checksum. IE the checksum is only the checksum of the header in the payload.

    :param input:
    :return:
    """
    PacketAccess.getHeader(input)
    div = CHECKSUM_POLYNOMIAL
    remainder = 0
    return remainder

def checkChecksum(packet):
    checksum = PacketAccess.getChecksum(packet)
    calcedChecksum = calcChecksum(packet)
    # Note: could also verify by appending the remainder (checksum) to the packet header and running checksum on that, expecting a remainder of 0.
    return checksum == calcedChecksum

def partialPacketInfoFromBytes(bytes):
    t = s.unpack_from(HEADER_FMT, bytes, 0)
    return t[2], t[3]

def setValue(packet, key, value):
    try:
        if type(packet) == bytes:
            packet = bytearray(packet)
        s.pack_into(HEADER_FMT_DICT[key]['fmt'], packet, HEADER_FMT_DICT[key]['offset'], value)
    except s.error as msg:
        print(f"Cannot set value {value} for packet {packet} due to following error: ", msg)
    return packet

def getValue(packet, key):
    return s.unpack_from(HEADER_FMT_DICT[key]['fmt'], packet, HEADER_FMT_DICT[key]['offset'])[0]

def defaultHeader(packetID=0, packetNum=1, totalPackets=1, payloadSize=0, checksum=0):
    d = OrderedDict({
        PACKET_ID_KEY: packetID,
        PACKET_NUM_KEY: packetNum,
        TOTAL_PKT_KEY: totalPackets,
        PAYLOAD_SIZE_KEY: payloadSize,  # only the size after the header
        CHECKSUM_KEY: checksum
    })
    return dictToHeader(d)

def bytesToDict(bytes):
    t = s.unpack_from(HEADER_FMT, bytes, 0)
    ret = {}
    i = 0
    for key, value in HEADER_FMT_DICT.items():
        ret[key] = t[i]
        i += 1
    return ret

def dictToHeader(hDict):
    newHeader = bytes(HEADER_SIZE)
    for key, val in hDict.items():
        offset = HEADER_FMT_DICT[key]['offset']
        fmt = HEADER_FMT_DICT[key]['fmt']
        s.pack_into(fmt, newHeader, offset, val)
    return newHeader