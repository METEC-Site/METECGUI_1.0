from Applications.METECControl.LoRa.LoRaHeaders import HANDSHAKETYPE
from Utils.TimeUtils import nowEpoch


class LoRaHANDSHAKEPKG:
    def __init__(self, timestamp=None, payload=None, handShakeType=HANDSHAKETYPE.Other, **kwargs):
        self.handShake = handShakeType
        self.timestamp = timestamp if timestamp else nowEpoch()
        self.payload = payload
