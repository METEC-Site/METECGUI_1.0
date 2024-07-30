import datetime

import Applications.METECControl.LoRa.LoRaHeaders as LH
from Applications.METECControl.LoRa.fakeMiddleMan import dataQ
from Framework.BaseClasses.Channels import ChannelType

OPERATIONAL = True
TIMEDELTA = datetime.timedelta(seconds=3600)


class ProxyHandler:
    def __init__(self, LoRaProxy):
        self.LP = LoRaProxy

    def proxyManager(self):
        while OPERATIONAL:
            data = dataQ.get()

            if data.ChannelType == ChannelType.Data:
                self.package(data)

            if data.ChannelType == ChannelType.ProxyHandshake:
                self.handshake(data)

    def package(self, data):
        print(data.payload)

    def handshake(self, handshake):
        if handshake.handShakeType == LH.HANDSHAKETYPE.Join:
            return

        if handshake.handShakeType == LH.HANDSHAKETYPE.Leave:
            return

        if handshake.handShakeType == LH.HANDSHAKETYPE.IDCheck:
            return
