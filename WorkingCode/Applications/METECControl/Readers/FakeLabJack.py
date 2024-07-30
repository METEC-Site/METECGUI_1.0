""""
#######
FakeLabJack
#######

:Authors: Aidan Duggan
:Date: April 20, 2019

.. lab-jack-class:

A custom implementation of a modbus wrapper intended for use at CSU METEC.

"""
from Framework.BaseClasses.Channels import ChannelType

__docformat__ = 'reStructuredText'

import logging
from enum import Enum
import random

# from Applications.METECControl.Readers.Modbus import Modbus as MB
# from Framework.BaseClasses.Channels import ChannelType
from Applications.METECControl.Readers.LabJack import LabJack
from Framework.BaseClasses.Commands import CommandMethod
from Utils import TimeUtils

MAX_NUM_RETRIES = 10
class FakeLabJack(LabJack):
    def __init__(self, archiver, commandManager, dataManager, eventManager, name=None, IP=None, port=52361, blocking=True, qtimeout=None, readPipe=None, readInterval=1, connectionHeartbeat=10, **kwargs):
        LabJack.__init__(self, archiver, commandManager, dataManager, eventManager, name=name, IP=IP, port=port, blocking=blocking, qtimeout=qtimeout, readPipe=readPipe, readInterval=readInterval, connectionHeartbeat=connectionHeartbeat, **kwargs)
        # Destination.__init__(self, name=name)
        # Reader.__init__(self, name=name)
        # CommandClass.__init__(self, name=name, commandManager=commandManager)
        self.blocking=blocking
        self.qtimeout=qtimeout
        self.IP = IP
        self.port = port
        self.name = name
        self.configs = {}
        self.devices = {}
        self.deviceConfiguration = []
        self.writeBuffers = {}
        self.readAllBuffers = {}
        self.connected = False
        self.archiver =archiver
        self.eventManager=eventManager
        self.commandManager = commandManager

    def __enter__(self):
        self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __del__(self):
        self.disconnect()

    # def start(self):
    #     Destination.start(self)

    def handlePackage(self, package):
        if package.channelType == ChannelType.Command:
            self.executeCommand(package)

    def handleResponse(self, package):
        pass

    def getName(self):
        return self.name

    def addDevice(self, name=None, device_type=None, pin=None, **kwargs):
        LabJack.addDevice(self, name, device_type, pin, **kwargs)
        try:
            self.devices[name]['state'] = random.randint(0, 1)
        except: pass

    @CommandMethod
    def connect(self):
        """ A wrapper for the modbus connect method. Device configuration and resetting buffers will occur every
        time this happens."""

        # read a single value, the product ID, from the FakeLabJack.
        self.connected = True
        return self.connected

    def disconnect(self):
        """ A wrapper for the modbus disconnect method. """
        self.connected = False

    @CommandMethod
    # @CookRead
    def read(self):
        self.cook = True
        """
        makes fake data

        Return
        ----------
        A dictionary containing the timestamp, source ID, and data values of all data received from the FakeLabJack. If a
        query returns no data values, the key/value pair is omitted from this return dictionary (Though the metadata will
        be present in a getReaderMetadata command)
        """

        ret = {}
        for devicename, values in self.devices.items():
            if values["item_type"] == "Thermocouple":
                # temperature = 50
                temperature = 50+random.randint(-15, 15)
                ret[devicename] = temperature
            elif values["item_type"] == "Electric Valve":
                ret[devicename] = self.devices[devicename]["state"]
            # elif values["item_type"] == "Flow Meter":
            #     v_min = float(values["min"])
            #     v_max = float(values["max"])
            #     ret[devicename] = (v_max - v_min)/2+v_min + random.randint(-5,5)
            else:
                offset = float(values.get("offset",0))
                slope = float(values.get("slope",0))
                v_min = float(values.get("min", 0))
                v_max = float(values.get("max",5))
                if offset:
                    v_min-=offset
                    v_max-=offset
                if slope:
                    v_min/=slope
                    v_max/=slope
                delta = v_max-v_min
                val = (v_max - v_min) / 2 + v_min + random.uniform(-delta/10, delta/10)
                ret[devicename] = val

            # if ret is empty, return it. Otherwise, attach a timestamp and source to the data within the ret dictionary.
            if not ret:
                return ret
        ret["timestamp"] = TimeUtils.nowEpoch()
        ret['source'] = self.name
        return ret

    def _configureThermocouple(self, device):
        pass

    @CommandMethod
    def openValve(self, valve):
        """ Issue an open valve command to a specified valve

        Parameters
        ----------
        valve : str
            The valve must be in self.devices.keys()
        """
        #TODO: put check(s?) in helper function.
        if valve in list(filter(lambda x: self.devices[x]['item_type'] == 'Electric Valve', self.devices)):
            self._openValve(valve)
            return True
        else:
            logging.log(level=logging.DEBUG, msg='valve {} not found in {}\'s devices'.format(valve, self.name))
            return False

    def writeDevice(self, deviceName, data):
        """ A funciton to write data to a modbus address associated with a device.

        Notes
        ----------
        The data will be written to an address on the FakeLabJack if the device associated with deviceName contains "W" in
            that pin's access.

        Parameters
        ----------
        deviceName : str
            deviceName must be included in self.devices.keys()
        data : device specific
            data to write to a device.

        """
        with self.lock:
            if not self.connected:
                self.connect()
            if self.devices.get(deviceName):
                device = self.devices[deviceName]
                device["state"] = data


class TemperatureTypes(Enum):
    """
    Specified by modbus thermocouple protocol
    """
    K = 0
    C = 1
    F = 2

"""
Thermocouple type to integer value as specified by thermocouple protocol.
"""
TCOUPLE_TYPES_TO_INDEX = {
    "E": 20,
    "J": 21,
    "K": 22,
    "R": 23,
    "T": 24,
    "S": 25,
    "C": 30
}