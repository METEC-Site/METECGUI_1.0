import pickle

import Framework.Proxy.SimplifiedProxyHeader as ph
from Utils import Encoding as en

TYPE_MAP = {
    "char":   "c",
    'None':   "c",  # null char b'\x00'
    "bool":   "?",
    "INT8":   "b",
    "UINT8":  "B",
    "INT16":  "h",
    "UINT16": "H",
    "INT32":  "i",
    "UINT32": "I",
    "INT64":  "q",
    "UINT64": "Q",
    "FLOAT32": "f",
    "DOUBLE": "d",
    'STRING': 's'  # char[]
}

class SerializeTypeError(Exception):
    pass

def getType(val, longname=False):  #if none is returned, convert val to a string (likely unknown enum)
    ret=''
    length=''
    if val is None:
        # TODO: None types set to Bool type instead. Void type is only for native endian
        ret = 'None'
    elif type(val) is int:
        if val < 0:
            ret = "INT8"
            if val < 128:
                ret = "INT16"
            if val < -32768:
                ret = "INT32"
            if val < -2147483648:
                ret = "INT64"
        else:
            ret = "UINT8"
            if val > 255:
                ret = "UINT16"
            if val > 65535:
                ret = "UINT32"
            if val > 4294967295:
                ret = "UINT64"
    elif type(val) is float:
        ret = 'DOUBLE'
    elif type(val) == str:
        if len(val.encode()) == 1:
            ret = 'char'
        else:
            length = str(len(str(val).encode()))
            ret = 'STRING'
    else:
        return None
    if longname:
        return ret
    else:
        return length+TYPE_MAP[ret]

def getKey(d, v):
    for key, value in d.items():
        if v == value:
            return key

def serialize(data, newLine = True):
    # expecting a dictionary of binary or string data.
    jsonData = en.restrictedJSONDumps(data)
    if newLine:
        lineData = ''.join([jsonData, '\n'])
    else:
        lineData = jsonData
    serData = lineData.encode('ascii')
    return serData

def deserialize(serData):
    lineData = serData.decode('ascii')
    jsonData = lineData.strip('\n')
    data = en.restrictedJSONLoads(jsonData)
    return data

def makeRepeaterDicts(package, radioID):
    # make a dictionary from the package
    dictPackage = package.toDict()
    serPackage = serialize(dictPackage, newLine=False) # get the singular, large serialized package.




    return pickle.dumps({
        "dest_addr": radioID,
        "payload": plBytes
        })

def getRepeaterDict(bytes):
    return pickle.loads(bytes)

# making packet from
def makePacket(packetType, sourceID, destinationID, packetID, packetNum, totalPackets, channelType, payloadSize,
               checksum):
    header = ph.defaultHeader()


###### CHONKER? #######

def splitPackets(packet, maxBytes):
    """
    splits packet into list of smaller packets with headers depending on maximum size in bytes
    :param packet: packet to split up
    :param maxBytes: maximum bytes of payload, not header+payload
    :return: list of packets
    """
    sendPackets = []
    headSize = ph.HEADER_SIZE
    dataSize = len(packet[ph.HEADER_SIZE:])
    hDict = ph.bytesToDict(packet)
    if dataSize > maxBytes:
        numFullPackets = int(dataSize / maxBytes)
        lastPackSize = dataSize - (numFullPackets * maxBytes)
        hDict['totalPackets'] = numFullPackets
        if lastPackSize > 0:
            hDict['totalPackets'] += 1
        for i in range(numFullPackets):
            i += 1
            hDict['packetNum'] = i
            hDict['packetSize'] = maxBytes
            headBytes = ph.dictToBytes(hDict)
            startI=headSize + (i - 1) * maxBytes
            endI=(headSize+i*maxBytes)
            sendPackets.append(headBytes + packet[startI:endI])

        if lastPackSize>0:  # If packet size does not divide evenly by maxBytes
            hDict['packetNum'] = numFullPackets+1
            hDict['totalPackets'] = numFullPackets+1
            hDict['packetSize'] = lastPackSize
            headBytes = ph.dictToBytes(hDict)
            sendPackets.append(headBytes + packet[headSize + numFullPackets * maxBytes:])
    else:
        sendPackets.append(packet)
    return sendPackets


def combinePackets(packets: list):
    """
    Combines list of packet bytes
    :param packets: list of packet bytes ordered by packetNum
    :return: single packet bytes
    """
    hDict = ph.bytesToDict(packets[-1])
    packetData = bytearray()
    for packet in packets:
        packetData += packet[ph.HEADER_SIZE:]
    hDict['packetSize'] = len(packetData)
    hDict['totalPackets'] = 1
    hDict['packetNum'] = 1
    return ph.dictToBytes(hDict)+packetData

############## Authenticator ##############

def makeHandshake(proxyName, proxyNamespace):
    handshake = {
        'proxyNamespace': proxyNamespace,
        'proxyName': proxyName
    }
    serialized = pickle.dumps(handshake)
    packetType = ph.PacketTypes.handshake.value
    header = ph.defaultHeader(packetType=packetType)
    completePacket = ph.dictToBytes(header) + serialized
    return completePacket


def decodeHandshakePacket(handshakePacket:bytes):
    """ handshakePacket includes header"""
    if ph.checkChecksum(handshakePacket):
        if ph.PacketAccess.getPacketType(handshakePacket) == ph.PacketTypes.handshake.value:
            handshake = pickle.loads(handshakePacket[ph.HEADER_SIZE:])
            if type(handshake) is dict:
                keys = handshake.keys()
                if 'proxyNamespace' in keys and 'proxyName' in keys and len(keys) == 2:
                    return handshake
    return False



def _packageSize(package):
    size=0
    size+=package.channelType.__sizeof__()
    # size+=package.timestamp.__sizeof__()
    for k, v in package.payload.items():
        size+= k.__sizeof__() + v.__sizeof__()
    return size

if __name__ == '__main__':
    data = pickle.dumps(12345)
    head = ph.dictToBytes(ph.defaultHeader(payloadSize=len(data), packetNum=1, totalPackets=1))

    # print('data', data)
    initial = head+data
    # print("initial", initial)
    b = splitPackets(initial, 2)
    # print(b)
    combined = combinePackets(b)
    # print('combined   ', combined)
    # print('header', head, '\nsplit', b, '\ncombined', combined)
    # print("data equal = ", initial[ph.HEADER_SIZE:], initial[ph.HEADER_SIZE:] == data)
    # print("header equal", combined[:ph.HEADER_SIZE] == initial[:ph.HEADER_SIZE])
    print("ProxySerializer passes?", combined == initial)
