import logging
from struct import *

from Applications.METECControl.LoRa.LoRaHeaders import HEADERS
from Applications.METECControl.LoRa.fakeMiddleMan import packageQ
from Framework.BaseClasses.Channels import ChannelType

MAX_DATA_LENGTH = 200
HEADER_LENGTH = 9


# def piping(config, LoRaMod, config):
#     LoRaPipe = ThreadedPipe([LoRaMod])
#     LoRaHandler = ThreadedPipeHandler.ThreadedPipeHandler(config['logChannelName'], self.LoRaPipe)
#     sLoRaPipe.start()


class TRANSMISSION:
    def __init__(self, config):
        self.transmissonID = 0
        # test = TEST()
        #
        # piping(LoRaMod=test, config=config)
        #
        # self.LoRaPipe = ThreadedPipe([self.test])
        # LoRaHandler = ThreadedPipeHandler.ThreadedPipeHandler(config['logChannelName'], self.LoRaPipe)
        # self.LoRaPipe.start()

    def radioPrep(self, data, dataType, packageID=0):
        data = self.dataLength(bytearray(data))
        payloadType = None

        transmissonLength = pack(HEADERS.Transmission, len(data))
        transmissonID = pack(HEADERS.TransmissionID, self.transmissonID)
        self.transmissonID += 1
        packageID = pack(HEADERS.PackageID, packageID)

        if dataType == ChannelType.ProxyHandshake:
            payloadType = HEADERS.Handshake

        if dataType == ChannelType.Data:
            payloadType = HEADERS.Data

        if payloadType == None:
            logging.info("DataType Error in radioPrep. Payload Not Prepped. No Transmission")
            return

        transmissonPosition = 1
        for payload in data:
            transmissonNum = pack(HEADERS.Transmission, transmissonPosition)
            transmissonPosition += 1
            payloadLength = pack(HEADERS.PayloadLength, len(payload))

            finalPackage = bytearray(payloadType + transmissonNum + transmissonLength + payloadLength + payload + packageID + transmissonID)

            packageQ.put(finalPackage)

    def dataLength(self, data):
        dataList = []

        if (len(data) + HEADER_LENGTH) < MAX_DATA_LENGTH:
            dataList.append(data)
            return dataList

        else:
            while (len(data) + HEADER_LENGTH) > MAX_DATA_LENGTH:
                dataSegment = data[:(MAX_DATA_LENGTH - HEADER_LENGTH)]
                dataList.append(dataSegment)
                del data[:(MAX_DATA_LENGTH - HEADER_LENGTH)]

            dataList.append(data)

        return dataList
