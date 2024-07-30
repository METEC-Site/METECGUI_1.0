"""
.. _lab-jack-class:

#######
LabJack
#######

:Authors: Aidan Duggan
:Date: April 20, 2019
:Version: 1.3

A LabJack reader using Modbus commands for Controller boxes at CSU METEC.

"""
__docformat__ = 'reStructuredText'

import csv
import pathlib
import re
import socket
import struct as s
import threading
from copy import deepcopy
from enum import Enum

from Applications.METECControl.Readers.Modbus import Modbus as MB
from Framework.BaseClasses import Events
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Commands import CommandClass, CommandMethod
from Framework.BaseClasses.Destination import Destination
from Framework.BaseClasses.Package import Package
# from Framework.BaseClasses.Readers.Reader import Reader
from Framework.BaseClasses.Readers.IntervalReader import IntervalReader
from Utils import TimeUtils, Errors

LJ_REGISTERS_FILE = pathlib.Path(pathlib.Path(__file__).parent).joinpath("ljPins", "pins_to_registers.csv")
LJ_DIO_FILE       = pathlib.Path(pathlib.Path(__file__).parent).joinpath("ljPins", "pin_to_dio.csv")

MAX_NUM_RETRIES = 10
class LabJack(IntervalReader, CommandClass, Destination):
    """
    A class designed to communicate with a labjack device over modbus.

    To Instantiate Properly either:
    1) Call the Factory method that will pass in configuration information properly and automatically. Globally unique
    name and IP must be specified by configuration files in the Factory file.
    or
    2) Instantiate object, pass in properly created configuration files, call setBuffers(), add each device manyally (and
    properly pass its property list) then configureDevices, and then connect. Globally unique name and IP must be specified by user.
    Or just let the factory do all that for you.

    """
    tid=0
    def __init__(self, archiver, commandManager, dataManager, eventManager,
                 name=None, IP=None, port=52362,
                 fields=None, controller=None, processGroup=None, upstreamGSH=None,
                 blocking=True, qtimeout=None, readPipe=None, readInterval = 1,
                 **kwargs):
        super().__init__(name=name, dataManager=dataManager, commandManager=commandManager, readInterval=readInterval, readPipe=readPipe, **kwargs)

        self.archiver = archiver
        self.eventManager = eventManager # todo: put this in a base class
        self.LJLock = threading.RLock()
        self.IP = IP
        self.modbus = MB(IP, port, name=name, connType=socket.SOCK_DGRAM)
        self.blocking=blocking
        self.qtimeout=qtimeout
        self.port = port
        self.controller=controller
        self.processGroup=processGroup
        self.upstreamGSH = upstreamGSH

        self.configs = {}
        self.devices = {}
        self.deviceConfiguration = []
        self.writeBuffers = {}
        self.readAllBuffers = {}
        self.connected = False

        self.pinsConfig = self.importPinConfig(LJ_REGISTERS_FILE)
        self.dioConfig = self.importPinConfig(LJ_DIO_FILE)

        for fieldName, fieldInfo in fields.items():
            device_type = self.deviceTypeFromName(fieldName)
            self.addDevice(fieldName, device_type=device_type, **fieldInfo)

    def deviceTypeFromName(self, fieldName):
        for deviceSignifier in FieldMapping.keys():
            if deviceSignifier in fieldName:
                return FieldMapping[deviceSignifier]
        return "Unknown"

        # sets up the read pipe. If readPipe exists, set self.readPipe to this, else make a new one with
        # readInterval and dataManager as params (and self.readPipe is set to that).
        # self._timer = Timer(connectionHeartbeat, self._connectedStatusTimer)

    def __enter__(self):
        self.connect()

    def _onExitCleanup(self):
        self.disconnect()
        # self._timer.cancel()

    def start(self):
        """ Kicks of threading implementation and read pipe start methods, as well as the connection status timer."""
        IntervalReader.start(self)
        # self._timer.start()

    def end(self):
        IntervalReader.end(self)
        # self._timer.cancel()

    def handlePackage(self, package):
        if package.channelType == ChannelType.Command:
            self.executeCommand(package)

    def increaseTID(self):
        LabJack.tid = (LabJack.tid + 1) % 2**16

    @CommandMethod
    def getInfo(self):
        return deepcopy(self.devices)

    @CommandMethod
    def connect(self):
        """ A wrapper for the modbus connect method. Device configuration and resetting buffers will occur every
        time this happens."""

        # read a single value, the product ID, from the labjack.

        with self.lock:
            self.modbus.connect()
            sendBuffer = self.modbus.makeReadCommand(60000, 2, 0, 0, 0, 3)
            recvBuffer = bytearray(13)
            connected = self.modbus.sendRecv(sendBuffer, recvBuffer)

            # todo: log this (instead of sending an event?)
            if self.connected and (not connected):
                msg = f'Labjack {self.getName()} at IP:Port ({self.IP}:{self.port}) was connected but is now disconnected'
                discPld = Events.EventPayload(self.getName(), eventType=Events.EventTypes.Disconnected, msg = msg)
                discPkg = Package(self.getName(), payload=discPld, channelType=ChannelType.Event)
                if self.eventManager:
                    self.eventManager.accept(discPkg)
                else:
                    self.logger.error(msg)
            self.connected = connected
            return self.connected

    @CommandMethod
    def disconnect(self):
        """ A wrapper for the modbus disconnect method. """
        with self.lock:
            if self.connected:
                disconnected = self.modbus.disconnect()
                # disconnected will be True if the shutdown was successful, False if it was unsuccessful.
            self.connected = False
            return (not self.connected)

    @CommandMethod
    def getReaderMetadata(self, sourceName = None):
        """ A function responsible for returning metadata about the class instance.

        Return
        ----------
        A dictionary containing type information about timestamp, name/source, and data fields.
        """
        ret = {"timestamp": "datetime - UTC epoch"}
        for deviceName, props in self.devices.items():
            if props['data_type']:
                ret[deviceName] = props["data_type"]
        return ret

    @CommandMethod
    def read(self):
        """ Issue a (series of) modbus command(s) to the labjack to read all readable pins and extract the data from those queries.

        Notes
        ----------
        Issues commands to read a series of blocks of registers from the modbus. Within the totality of the blocks are
        contained each device's pin's read address.
        To read, the labjack must call its connect method. In order for this to occur, buffers will be set and the
        sub devices will be configured.

        Return
        ----------
        A dictionary containing the timestamp, source ID, and data values of all data received from the labjack. If a
        query returns no data values, the key/value pair is omitted from this return dictionary (Though the metadata will
        be present in a getReaderMetadata command)
        """
        # TODO: make checks to ensure proper TID in receiving buffer matches the command buffer.
        ret = {}
        # TODO: go over connect functionality for this and Alicat. Want to connect every time?
        # TODO: adjust functionality to account for errors in reading from modbus. IE don't break if the modbus throws an error.
        #   either do a try catch or look into locking.
        with self.lock:
            self.connect()
            if not self.connected:
                return ret

            #send configuration information for each pin that needs it.
            self._configurePins()

            for commandKey in self.readAllBuffers.keys():
                commandBuffer = self.readAllBuffers[commandKey]["command"]
                responseBuffer = self.readAllBuffers[commandKey]["response"]
                format = self.readAllBuffers[commandKey]["format"]
                try:
                    self.modbus.setTID(commandBuffer, LabJack.tid)
                    self.increaseTID()
                except Errors.BufferError:
                    self.logger.debug(msg="TID {} not set for buffer {} on device {}".format(LabJack.tid, commandBuffer, self.getName()))

                sendRecvSuccess = self.modbus.sendRecv(commandBuffer, responseBuffer)
                if sendRecvSuccess:

                    # check commandID and responseTID against each other to make sure that they match.
                    comtid = resptid = tidSuccess = 1
                    try:
                        comtid = self.modbus.getTID(commandBuffer)
                        resptid = self.modbus.getTID(responseBuffer)
                    except Exception as e:
                        tidSuccess = 0
                    if not (comtid == resptid) or (tidSuccess == 0):
                        self.logger.debug(
                        'Response transaction didn\'t match for command TID: {} on labjack {}'.format(comtid, self.getName()))

                    # extract the data and parse it, associating each piece of data in the buffer with the corresponding
                    # device/field.
                    data = self.modbus.extractData(format, responseBuffer)
                    deviceNames = self.readAllBuffers[commandKey]["devices"]

                    if data:
                        if self.readAllBuffers[commandKey]['start_address_name'] == 'DIO_STATE':
                            # unpack the data if it is within the DIO state register. When creating the buffers, the
                            # DIO_STATE register is read alone, without reading the surrounding registers.
                            # TODO: Make sure this is the case
                            for deviceName in deviceNames:
                                ret[deviceName] = self.dioStateReader(data, deviceName)
                        else:
                            ret = {**ret, **dict(zip(deviceNames, data))}

            # if ret is empty, return it. Otherwise, attach a timestamp and source to the data within the ret dictionary.
            if not ret:
                return ret
            ret["timestamp"] = TimeUtils.nowEpoch()
            return ret

    def importPinConfig(self, configPath):
        with self.LJLock:
            cfg = {}
            with open(configPath) as cfgFile:
                dr = csv.DictReader(cfgFile)
                for line in dr:
                    if 'start_address' in line:
                        line['start_address'] = int(line['start_address'])
                    cfg[line['pin']] = line
            return cfg

    def _configureThermocouple(self, device):
        if device['item_type'] == 'Thermocouple':
            if not "output_units" in device.keys():
                device["output_units"] = 'F'

            AIN = device['pin']
            readPin = AIN + "_EF_READ_A"
            readInfo = self.pinsConfig[readPin]
            for key in readInfo.keys():
                device[key] = readInfo[key]
            cfg = {
                AIN + "_EF_INDEX": TCOUPLE_TYPES_TO_INDEX[device['thermocouple_type']],
                AIN + "_EF_CONFIG_A": TemperatureTypes[device["output_units"]].value,
                AIN + "_EF_CONFIG_B": 60052,
                AIN + "_EF_CONFIG_D": 1.0,
                AIN + "_EF_CONFIG_E": 0.0
            }
            for writeLine in cfg.items():
                resp = self.modbus.makeWriteResponse()
                pinName = writeLine[0]
                pinInfo = self.pinsConfig[pinName]
                startAddr = int(pinInfo["start_address"])
                numreg = self.modbus.getNumRegisters(pinInfo["data_type"])
                command = self.modbus.makeWriteCommand(startAddr=startAddr, numreg=numreg, data=writeLine[1],
                                                dataTypes=pinInfo["data_type"])
                self.deviceConfiguration.append({'name':device['name'], 'command': command,'response': resp})
                device['configured'] = False

    def _configurePins(self):
        for configInfo in list(self.deviceConfiguration):
            name = configInfo['name']
            command = configInfo['command']
            response = configInfo['response']
            status = self.modbus.sendRecv(command, response)
            # if status is True, the command and response were both sent. Otherwise, the command failed.
            try:
                func = self.modbus.getFUNC(response)
                received = True
            except Exception as e:
                func = 0x80
                received = False
            if not status:
                # status was incorrect, couldn't send the command to configure and/or receive the success response
                received = False
            elif func & 0x80:
                # Error function received from the labjack.
                received = False
            if received:
                # remove the device from the list that needs to be configured, and set the configured property in the
                # device dictionary to True.
                self.devices[name]['configured'] = True
                self.deviceConfiguration.remove(configInfo)
            else:
                self.logger.debug(f'couldn\'t set configuration buffer {command} for {self.getName()}')


    def _isPinWritable(self, pinName):
        access = self.pinsConfig[pinName]['access']
        if "W" in access:
            return True
        return False

    def _isPinReadable(self, pinName):
        access = self.pinsConfig[pinName]['access']
        if "R" in access:
            return True
        return False

    def _isPinConfigurable(self, pinName):
        access = self.pinsConfig[pinName]['access']
        if "C" in access:
            return True
        return False

    def _isPinDIO(self, pinName):
        if 'DIO' in pinName or 'MIO' in pinName or 'FIO' in pinName or 'EIO' in pinName or 'CIO' in pinName:
            return True
        return False

    def _DIOSubstitute(self, device):
        if not device['pin'] in self.dioConfig.keys():
            return False
        # dio = list(filter(lambda x: (self.pinsConfig[x]['start_address'] == device['start_address'] and
        #                               'DIO' in self.pinsConfig[x]['pin']), self.pinsConfig.keys()))[0]
        device['pin'] = self.dioConfig[device['pin']]['dio']

    def _getPinProperties(self, pinName):
        return self.pinsConfig.get(pinName, {})

    def _addDIORead(self, device):
        pinProperties = self._getPinProperties('DIO_STATE')
        dioStart = pinProperties['start_address']
        dioType = pinProperties['data_type']
        if not dioStart in self.readAllBuffers.keys():
            readCommand = self.modbus.makeReadCommand(dioStart, self.modbus.getNumRegisters(dioType))
            readResponse = self.modbus.makeReadResponse(self.modbus.getNumRegisters(dioType))
            self.readAllBuffers[dioStart] = \
                {'command': readCommand,
                 'response': readResponse,
                 'start_address_name': 'DIO_STATE',
                 'number_registers': 2,
                 'format': ">I",
                 'devices': []}
        self._DIOSubstitute(device)
        self.readAllBuffers[dioStart]['devices'].append(device['name'])
        self.devices[device['name']] = device

    def _invalidPinsInRange(self, firstPinName, lastPinName):
        pin = firstPinName
        startAddress = self._getPinProperties(firstPinName)['start_address']
        lastAddress = self._getPinProperties(lastPinName)
        if lastAddress['start_address'] + s.calcsize(self.modbus.TYPE_MAP[lastAddress['data_type']]) - startAddress >= self.modbus.MAX_READ_REG:
            return True
        i = 0
        while not pin == lastPinName and not i >= self.modbus.MAX_READ_REG:
            pinProps = self._getPinProperties(pin)
            thisPin = pinProps['pin']
            if self._isPinConfigurable(thisPin) or not self._isPinReadable(thisPin) or self._isPinDIO(thisPin):
                return True
            pin = pinProps['next_pin']
            i = pinProps['start_address']-startAddress
        return False

    def addDevice(self, name=None, device_type=None, pin=None, **kwargs):
        device = {
            'name': name,
            'item_type': device_type,
            **kwargs
        }
        device = dict(**device, **(self._getPinProperties(pin)))
        if not 'pin' in device.keys():
            return False
        self._configureThermocouple(device)

        #Make read/write buffers
        if self._isPinWritable(device['pin']):
            numreg = self.modbus.getNumRegisters(device['data_type'])
            command = self.modbus.makeWriteCommand(device['start_address'], numreg, dataTypes=self.modbus.TYPE_MAP[device['data_type']])
            response = self.modbus.makeWriteResponse()
            self.writeBuffers[name] = {'command': command,
                                       'response': response}
        if self._isPinReadable(device['pin']):
            if self._isPinDIO(device['pin']):
                self._addDIORead(device)
            else:
                devAddr = int(device['start_address'])
                closestAddresses = list(self.readAllBuffers.keys())
                closestAddresses.sort(key=lambda x: abs(x - devAddr))
                for closeAddr in closestAddresses:
                    closestProps = self.readAllBuffers.pop(closeAddr)
                    startPin = device['pin'] if devAddr < closeAddr else closestProps['start_address_name']
                    endPin = device['pin'] if devAddr >= closeAddr else closestProps['start_address_name']
                    if self._invalidPinsInRange(startPin, endPin):
                        self.readAllBuffers[closeAddr] = closestProps
                    else:
                        curFormat = closestProps['format']
                        curStart= closestProps['start_address']
                        curEnd = int(curStart + s.calcsize(curFormat)/2)
                        startAddress, fmt, devices = None, None, None
                        if devAddr < curStart:
                            devFmt = ">{}".format(self.modbus.TYPE_MAP[device['data_type']])
                            numX = int((curStart-devAddr) * 2 - s.calcsize(devFmt))
                            fmt = devFmt + 'x' * numX + closestProps['format'].strip('<>')
                            startAddress = devAddr
                            devices = [name, *closestProps['devices']]
                        elif curStart < devAddr and devAddr < curEnd:
                            startAddress = curStart
                            newDevIdx = 0
                            iterFmt = ""
                            trimFmt = curFormat.strip('<>')
                            devFmt = self.modbus.TYPE_MAP[device['data_type']]
                            for i in range(0, len(trimFmt)):
                                iterFmt += trimFmt[i]
                                if not trimFmt[i] in 'x><':
                                    newDevIdx += 1
                                endAddr = curStart + int(s.calcsize(iterFmt)/2)

                                if endAddr == device['start_address'] and trimFmt[i+1:i+1+s.calcsize(devFmt)] == 'x'*s.calcsize(devFmt):
                                    fmt = '>' + iterFmt + self.modbus.TYPE_MAP[device['data_type']]
                                    fmt = fmt + trimFmt[i+1+s.calcsize(devFmt):]
                                    closestProps['devices'].insert(newDevIdx, device['name'])
                                    devices = closestProps['devices']
                                    break
                        elif curEnd <= devAddr:
                            devFmt = "{}".format(self.modbus.TYPE_MAP[device['data_type']])
                            numX = int((devAddr-(curEnd)) * 2)
                            fmt = closestProps['format'] + 'x' * numX + devFmt
                            startAddress = curStart
                            devices = [*closestProps['devices'], name]
                        else:
                            return True ## This happens if the device is added twice. (curStart == devAddr)
                        numreg = int(s.calcsize(fmt)/2)
                        closestProps['command'] = self.modbus.makeReadCommand(startAddress, numreg)
                        closestProps['response'] = self.modbus.makeReadResponse(numreg)
                        closestProps['start_address'] = startAddress
                        closestProps['start_address_name'] = startPin
                        closestProps['number_registers'] = int(s.calcsize(fmt)/2)
                        closestProps['format'] = fmt
                        closestProps['devices'] = devices
                        self.readAllBuffers[startAddress] = closestProps
                        device['next_pin'] = self._getPinProperties(device['pin'])['next_pin']
                        self.devices[name] = device
                        return True
                fmt = '>{}'.format(self.modbus.TYPE_MAP[device['data_type']])
                numreg = int(s.calcsize(fmt)/2)
                self.readAllBuffers[device['start_address']] = {
                    'command': self.modbus.makeReadCommand(device['start_address'], numreg),
                    'response': self.modbus.makeReadResponse(numreg),
                    'start_address': device['start_address'],
                    'start_address_name': device['pin'],
                    'number_registers': numreg,
                    'format': fmt,
                    'devices': [name]
                }
                device['next_pin'] = self._getPinProperties(device['pin'])['next_pin']
                self.devices[name] = device
                return True

    @CommandMethod
    def eStop(self):
        self.closeAllValves()

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
            self.logger.debug(msg='valve {} not found in {}\'s devices'.format(valve, self.getName()))
            return False

    def _openValve(self, valve):
        self.writeDevice(valve, 0)

    @CommandMethod
    def closeValve(self, valve):
        """ Issue a close valve command to a specified valve

        Parameters
        ----------
        valve : str
            The valve must be in self.devices.keys()
        """
        if valve in list(filter(lambda x: self.devices[x]['item_type'] == 'Electric Valve', self.devices)):
            self._closeValve(valve)
            return True
        else:
            self.logger.debug('valve {} not found in {}\'s devices'.format(valve, self.getName()))
            return False

    @CommandMethod
    def closeAllValves(self):
        try:
            for valve in list(filter(lambda x: self.devices[x]['item_type'] == 'Electric Valve', self.devices)):
                self._closeValve(valve)
        except Exception as e:
            self.logger.exception(str(e))
            return False
        finally:
            return True

    def _closeValve(self, valve):
        self.writeDevice(valve, 1)

    def writeDevice(self, deviceName, data):
        """ A funciton to write data to a modbus address associated with a device.

        Notes
        ----------
        The data will be written to an address on the labjack if the device associated with deviceName contains "W" in
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
            if self.devices[deviceName]:
                device = self.devices[deviceName]
                if "W" in device['access']:
                    buffer = self.writeBuffers[deviceName]["command"] if self.writeBuffers[deviceName]["command"] else None
                    response = self.writeBuffers[deviceName]["response"]
                    dataType = device["data_type"]
                    if buffer:
                        self.modbus.setWriteData(buffer, data, dataType)
                    else:
                        self.writeBuffers[deviceName]["command"] = buffer = self.modbus.makeWriteCommand(device["start_address"], self.modbus.getNumRegisters(device["data_type"]), data)
                    self.modbus.sendRecv(buffer, response)
                    self.increaseTID()
            else:
                self.logger.debug("No such device {} to send data {} to".format(deviceName, data))
                return False

    def dioStateReader(self, value, sensorName):
        if value:
            if type(value) == tuple:
                value = value[0]
            device = self.devices[sensorName]
            pin = device['pin']
            shift = int(re.sub('DIO', "", pin))
            mask = (1 << shift)
            value = (value & mask) >> shift
        return value

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

FieldMapping = {
    "EV": "Electric Valve",
    "TC": "Thermocouple",
    "PT": "Pressure Transducer",
    "FM": "Flow Meter"
}