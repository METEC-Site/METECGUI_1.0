"""
.. _alicatMFC-reader-module:

#################
Alicat MFC Reader
#################

:Authors: Aidan Duggan, Jerry Duggan
:Date: May 1, 2019

A module to provide communication and control to an Alicat Mass Flow Control device.

"""
__docformat__ = 'reStructuredText'

import csv
import datetime
import logging
import pathlib
import socket
from copy import deepcopy
from enum import Enum
from threading import RLock, Timer

import Utils.TimeUtils as tu
from Applications.METECControl.Readers.Modbus import Modbus as MB
from Framework.BaseClasses import Commands
from Framework.BaseClasses import Events
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Destination import Destination
from Framework.BaseClasses.Package import Package
from Framework.BaseClasses.Readers.IntervalReader import IntervalReader

"""
TODO: Test this class after changes. The changes include, but are not limited to: delegating modbus to internal object
rather than inheritance, changing how devices are added, eliminating a configuration dictionary being passed in through init.
"""

MAX_NUM_RETRIES = 10
PINS_LIST = pathlib.Path(pathlib.Path(__file__).parent).joinpath("alicatPins", "pins_to_registers.csv")

class AlicatMFCReader(IntervalReader, Commands.CommandClass, Destination):
    """ A class used to facilitate communication with an alicat device over Modbus TCP

    :param archiver:
    :param commandManager:
    :param dataManager:
    :param eventManager:
    :param name:
    :param deviceType:
    :param totalizer:
    :param IP:
    :param port:

    :type archiver: None or :ref:`Object inheriting from Archiver <archiver-base-class>`
    :type commandManager: None or :ref:`Object inheriting from CommandManager <command-manager-base-class>`
    :type dataManager:
    :type eventManager:
    :type name:
    :type deviceType:
    :type totalizer:
    :type IP:
    :type port:

    """
    def __init__(self, archiver, commandManager, dataManager, eventManager,
                 name=None, deviceType=None, totalizer=False, IP=None, port=502,
                 readInterval=1,
                 **kwargs):
        """ Upon instantiation, this device will create a TCP modbus connection that will be used for communication with
        the device.

        Parameters
        ----------
        name : str
            The identifier of the device used.
        deviceType : str
            Specifier of kind of device this is ('MFC', 'MFM', etc)
        totalizer : bool
            Whether or not this device uses a totalizer.
        IP
            IP address for this device
        port : int
            Port that this device uses. 502 is the default TCP port.
        """
        super().__init__(name=name, archiver=archiver, commandManager=commandManager, dataManager=dataManager, eventManager=eventManager, readInterval=readInterval, **kwargs)
        self.name = name
        self.IP = IP
        self.port = port
        self.modbus = MB(IP=IP, port=port,
                         connType=socket.SOCK_STREAM, modbusEndian=">", deviceEndian=">", maxReadReg=127, name=name)
        self.UID = 247
        self.setpoint = 0
        self.addr_offset = -1
        # self.addr_offset = 0
        self.pins = {}
        self.deviceType = deviceType
        self.totalizer = totalizer
        self.configs = {}
        self.pins = {}
        self.readAllBuffers = {}
        self.gasMixtures = {}
        self.devices = {}
        self.connected = False
        self.buffersSet = False
        self.eventManager = eventManager

        self.legacyAddresses = [21, 22, 23, 24, 46, 65, 2041, 2043, 2045, 2047, 2049, 2051, 2053, 2054, 2055, 2056, 2057, 2058, 2059]
        self.legacyAddresses = [x+self.addr_offset for x in self.legacyAddresses]
        self.configurableAddresses = [1050, 1051, 1052, 1053, 1054, 1055, 1056, 1057, 1058, 1059]
        self.configurableAddresses = [x + self.addr_offset for x in self.configurableAddresses]

        self.lock = RLock()
        self._timer = Timer(10, self._connectedStatusTimer)

        self.addConfig('pins', PINS_LIST)

    def __enter__(self):
        self.connect()

    def _onExitCleanup(self):
        self.disconnect()
        # self._timer.cancel()

    def start(self):
        self.setBuffers()
        IntervalReader.start(self)
        # self._timer.start()

    def end(self):
        # Destination.end(self)
        IntervalReader.end(self)
        # self._timer.cancel()

    def handlePackage(self, package):
        if package.channelType == ChannelType.Command:
            self.executeCommand(package)
        pass

    def addConfig(self, name, cfgPath):
        """A simple function for adding a list of configuration information. The 'name' parameter will be used by other
        methods to access this list, so make sure it conforms to those functions.

        Parameters
        ----------
        name : str
        Returns
        -------
        None
        """
        cfg = self.configs[name] = {}
        with open(cfgPath) as cfgFile:
            dr = csv.DictReader(cfgFile)
            for item in dr:
                if 'start_address' in item.keys():
                    item['start_address'] = int(item['start_address'])
                uniqueKey = None
                for i in range(0, len(item.values())):
                    uniqueKey = list(item.values())[i]
                    if not uniqueKey in cfg.keys():
                        break
                if uniqueKey:
                    cfg[uniqueKey] = item
        return cfg

    def removeLegacy(self, list):
        # list[:] = [x for x in list if not 'legacy' in x[0].lower()]
        list[:] = [x for x in list if not x[1] in self.legacyAddresses]
        return True

    def removeStatistic(self, list):
        list[:] = [x for x in list if not "statistic" in x[0].lower()]
        list[:] = [x for x in list if not (x[0].split('_')[0] in StatisticOutputs and not x[0].split('_')[0] in self.deviceType)]
        return True

    def removeConfigurable(self, list):
        list[:]= list[:] = [x for x in list if not x[1] in self.configurableAddresses]
        return True

    def removeTotalizer(self, list):
        if not self.totalizer:
            list[:] = [x for x in list if not "totalizer" in x[0].lower()]
        return True

    def setBuffers(self):
        """ A function that sets up the buffers that will be used in modbus communication.
        It is necessary to first provide config lists using the 'addConfig' method. Entries with the name 'pins' are expected.

        Returns
        -------
        None
        """
        if not "pins" in self.configs.keys():
            raise NameError

        for pin in self.configs['pins'].values():
            self.pins[pin['pin']] = {
                "start_address": int(pin["start_address"]) + self.addr_offset,
                "data_type": pin["data_type"],
                "access": pin["access"]
            }
            strt = self.pins[pin['pin']]['start_address']
            if "W" in pin["access"]:
                self.pins[pin['pin']]["write_buffers"] = {"request": self.modbus.makeWriteCommand(int(strt), self.modbus.getNumRegisters(pin["data_type"]), uid=self.UID),
                                               "response": self.modbus.makeWriteResponse()}
            if "R" in pin["access"]:
                self.pins[pin['pin']]["read_buffers"] = {"request": self.modbus.makeReadCommand(int(strt), self.modbus.getNumRegisters(pin["data_type"]), uid=self.UID, func=4),
                                            "response": self.modbus.makeReadResponse(self.modbus.getNumRegisters(pin["data_type"]))}

        if self.pins.keys():
            # TODO: Redo how read all works. Make it read all the pins, similar to the labjack.
            # TODO: Currently finds relevant information based on deviceType. Kinds sketchy. Redo to make it more stable.

            addrList = []
            for pinName, properties in self.pins.items():
                addrList.append([pinName, properties['start_address'], properties['data_type'], properties['access']])
            addrList.sort(key=lambda x: x[1])

            self.removeLegacy(addrList)
            self.removeStatistic(addrList)
            self.removeConfigurable(addrList)
            self.removeTotalizer(addrList)

            startAddr = 0
            numReg = 0
            for addrProps in addrList:
                addrName = addrProps[0]
                addr = addrProps[1]
                dataType = addrProps[2]
                access = addrProps[3]
                numX = addr - (startAddr + numReg)
                if not "R" in access:
                    startAddr = -1
                    numReg = -1
                elif addr - startAddr > numReg or 'C' in access or startAddr == -1 or numX > 0 or\
                        (numReg + self.modbus.getNumRegisters(dataType)) > self.modbus.MAX_READ_REG:
                    startAddr = addr
                    numReg = self.modbus.getNumRegisters(dataType)
                    self.readAllBuffers[startAddr] = {'command': None,
                                                      'response': None,
                                                      "registers": {}}
                if "R" in access:
                    if addr in self.readAllBuffers[startAddr]['registers'].keys():
                        self.readAllBuffers[startAddr]['registers'][addr].append(addrName)
                    else:
                        self.readAllBuffers[startAddr]['registers'][addr] = [addrName]
                    if (addr + self.modbus.getNumRegisters(dataType))-startAddr > numReg:
                        numReg = (addr + self.modbus.getNumRegisters(dataType))-startAddr
                    self.readAllBuffers[startAddr]['command'] = self.modbus.makeReadCommand(startAddr, numReg,  uid=self.UID, func=4)
                    self.readAllBuffers[startAddr]['response'] = self.modbus.makeReadResponse(numReg)
        self.buffersSet = True
        return True

    def addDevice(self, deviceName, deviceInfo):
        self.devices[deviceName] = deviceInfo

    def connect(self):
        """A function that acts as a wrapper around the modbus 'connect' method. Will call setBuffers, and doing so
        requires all configuration information to have been provided using the 'addConfig' method.

        Returns
        -------
        None
        """
        if not self.buffersSet:
            self.setBuffers()
        if not self.connected:
            self.connected = self.modbus.connect()
        return self.connected

    def checkConnection(self):
        #TODO: query the alicat for its status and use this in the connect method.
        return self.connected

    def disconnect(self):
        """ A function that acts as a wrapper around the modbus 'disconnect' method.

        Returns
        -------
        None
        """
        if self.connected:
            self.modbus.disconnect()
        self.connected = False

    def _connectedStatusTimer(self):
        if not self.connect():
            ePld = Events.EventPayload(eventType=Events.EventTypes.ConnectTimeout, msg=f'Alicat {self.name} connection timed out.')
            ePkg = Package(self.name, payload=ePld, channelType=ChannelType.Event)
            self.eventManager.accept(ePkg)
        self._timer = Timer(10, self._connectedStatusTimer)
        self._timer.start()

    @Commands.CommandMethod
    def eStop(self):
        self.setSetpoint(0)


    def read(self):
        """ Reads all buffers from the device and returns them with their matching names.
        As this requires a connection, the configuration information must be passed to the device first, before any
        reading can be done.

        Returns
        -------
        retData: dict
            a dictionary containing a timestamp of when the data was collected, the source (this device's name), and
            all of the buffers that were read (name: value pair in the dictionary)
        """
        with self.lock:
            retData = {}
            timestamp = tu.DTtoEpoch(datetime.datetime.utcnow())
            retData['timestamp'] = timestamp
            retData['source'] = self.name
            try:
                self.connect()
                if not self.connected:
                    return {}
                for startAddr, bufferProps in self.readAllBuffers.items():
                    self.modbus.sendRecv(bufferProps['command'], bufferProps['response'])
                    data = {}
                    for regAddr, regNames in bufferProps['registers'].items():
                        for regName in regNames:
                            fmt = ">" + (2*(regAddr-startAddr))*"x" + self.modbus.TYPE_MAP[self.pins[regName]['data_type']]
                            data[regName] = self.modbus.extractData(fmt, bufferProps['response'])
                            if data[regName] == False:
                                cmd = bufferProps['command']
                                resp = bufferProps['response']
                                logging.exception(f'{self.name} error in sending packet {cmd}, got a response {resp}')
                            if type(data[regName]) is tuple:
                                data[regName] = data[regName][0]
                    if data:
                        retData = {**retData, **data}
                return retData
            except ConnectionResetError:
                self.disconnect()
                self.connect()
                return {}

    def getReaderMetadata(self, sourceName=None):
        """ A function providing all the relevant metadata about this object.

        Returns
        -------
        retMeta: dict
            This dictionary has the metadata about what format the timestamp is in, the name of the device, and also
            the datatypes of all the readable buffers of the physical modbus device.
        """
        retMeta = {}
        retMeta["timestamp"] = "datetime - UTC epoch"
        retMeta['source'] = "string"
        # TODO: revert back to dynamically configured.
        # for pinName, pinItem in self.pins.items():
        #     retMeta[pinName] = pinItem['data_type']
        retMeta['COMMAND_ID'] = 'int'
        retMeta['COMMAND_STATUS'] = 'int'
        retMeta['GAS_NUMBER'] = 'int'
        retMeta['DEVICE_STATUS_LEAST'] = 'int'
        retMeta['DEVICE_STATUS_MOST'] = 'int'
        retMeta['MFC_PRESSURE'] = 'float'
        retMeta['MFC_FLOW_TEMPERATURE'] = 'float'
        retMeta['MFC_VOLUMETRIC_FLOW'] = 'float'
        retMeta['MFC_MASS_FLOW'] = 'float'
        retMeta['MFC_MASS_FLOW_SETPOINT'] = 'float'

        return retMeta

    @Commands.CommandMethod
    def increaseSetpoint(self):
        """A method to increase the alicat's setpoint by 1

        .. seealso:
            :ref:`CommandMethod <command-method>`

        :return: True
        """
        self.setpoint += 1
        self.setSetpoint(self.setpoint)
        return True

    @Commands.CommandMethod
    def decreaseSetpoint(self):
        """A method to decrease the alicat's setpoint by 1

        .. seealso:
            :ref:`CommandMethod <command-method>`

        Returns
        -------
        None
        """
        self.setpoint -= 1
        self.setSetpoint(self.setpoint)

    @Commands.CommandMethod
    def setSetpoint(self, setpoint):
        """ A method that will send a modbus command to set the Alicat setpoint to the specified setpoint

        :param setpoint: the setpoint that
        :type setpoint: float, int

        :return: True if the setpoint was set correctly, False if it wasn't set.
        """
        with self.lock:
            self.setpoint = setpoint
            setpointRequest = self.pins["SETPOINT"]["write_buffers"]["request"]
            setpointResponse = self.pins["SETPOINT"]['write_buffers']['response']
            type = self.pins["SETPOINT"]["data_type"]
            self.modbus.setWriteData(setpointRequest, data=setpoint, dataTypes=self.modbus.TYPE_MAP[type])
            self.modbus.sendRecv(sendBuffer=setpointRequest, recvBuffer=setpointResponse)
            return True

    """
    Interface functions that allow device specific functionality to an alicat.
    """

    @Commands.CommandMethod
    def mixGas(self, composition=None, gasMixtureIndex=255):
        """
        Behavior:
            If composition is specified but gasMixtureIndex is not, this function will send the composition to the Alicat
                along with the instruction to mix that percent, and save it under the index of 255.
            If composition was not specified, this function will search for an existing composition under the gasMixtureIndex
                provided and use that to instruct the Alicat. If it could not find an existing composition, the function
                will do nothing else and fail, returning False.
            The composition must

        Parameters
        ----------
        composition: dict
            Keys: short name of gas or its integer gas number.
            Values: % or fraction of this gas in the overall makeup.
            The sum of all values in this dict must be 1 or 100. Otherwise, this function returns false.
        gasMixtureIndex: int
            An integer with a value of either 0, or an int between 236 and 255. Defaults to 255

        Returns
        -------
        True if successful, False if it failed
        """
        if composition:
            if len(list(composition.keys())) > 5:
                return False
            comp = deepcopy(composition)
            total = 0
            for ID, percent in comp.items():
                if ID in GasNumbers.keys():
                    pass
                elif ID in GasNumbers.values():
                    newID = list(filter(lambda x: GasNumbers[x] == ID, GasNumbers.values()))[0]
                    del comp[ID]
                    comp[newID] = percent
                else:
                    return False
                total += percent
            if total ==1:
                mult = 10000
            elif total == 100:
                mult = 100
            else:
                return False
            currentNumber = 1
            self.gasMixtures[gasMixtureIndex] = {}
            for ID, percent in comp.items():
                gasIndex = deepcopy(self.pins['GAS_{}_INDEX'.format(currentNumber)])
                self.modbus.setWriteData(gasIndex['write_buffers']['request'], ID, gasIndex['data_type'])
                gasPct = deepcopy(self.pins['GAS_{}_PCT'.format(currentNumber)])
                self.modbus.setWriteData(gasPct['write_buffers']['request'], mult*percent, gasPct['data_type'])
                self.modbus.sendRecv(gasIndex['write_buffers']['request'], gasIndex['write_buffers']['response'])
                self.modbus.sendRecv(gasPct['write_buffers']['request'], gasPct['write_buffers']['response'])
                self.gasMixtures[gasMixtureIndex][f'GAS_{currentNumber}_INDEX'] = gasIndex
                self.gasMixtures[gasMixtureIndex][f'GAS_{currentNumber}_PCT'] = gasPct
                self.gasMixtures[gasMixtureIndex]['mult'] = mult
        else:
            if gasMixtureIndex in self.gasMixtures.keys():
                mult = self.gasMixtures[gasMixtureIndex].pop('mult')
                for key, dict in self.gasMixtures[gasMixtureIndex].items():
                    self.modbus.sendRecv(dict['write_buffers']['request'], dict['write_buffers']['response'])
                self.gasMixtures[gasMixtureIndex]['mult'] = mult
            else:
                return False

        if not gasMixtureIndex <= 255 and not gasMixtureIndex >=236 and not gasMixtureIndex == 0 or not type(gasMixtureIndex) is int:
            return False
        else:
            return self.commandDevice(2, gasMixtureIndex)

    @Commands.CommandMethod
    def getInfo(self):
        return self.devices

    @Commands.CommandMethod
    def changeGasNumber(self, gasTableIndex):
        return self.commandDevice(1, gasTableIndex)

    @Commands.CommandMethod
    def deleteGasMixture(self, gasMixtureIndex):
        self.commandDevice(3, gasMixtureIndex)

    @Commands.CommandMethod
    def tare(self, arg):
        if not arg in [0, 1, 2]:
            return False
        else:
            return self.commandDevice(4, arg)

    @Commands.CommandMethod
    def totalizerReset(self):
        return self.commandDevice(5, None)

    @Commands.CommandMethod
    def valveSetting(self, arg):
        if not arg in [0,1,2,3]:
            return False
        else:
            return self.commandDevice(6, arg)

    @Commands.CommandMethod
    def displayLock(self, arg):
        if not arg in range[0,1]:
            return False
        else:
            return self.commandDevice(7, arg)

    @Commands.CommandMethod
    def changeP(self, arg):
        if not arg < 65535 and not arg >= 0:
            return False
        else:
            return self.commandDevice(8, arg)

    @Commands.CommandMethod
    def changeD(self, arg):
        if not arg < 65535 and not arg >= 0:
            return False
        else:
            return self.commandDevice(8, arg)

    @Commands.CommandMethod
    def changeI(self, arg):
        if not arg < 65535 and not arg >= 0:
            return False
        else:
            return self.commandDevice(9, arg)

    @Commands.CommandMethod
    def changeLoopVar(self, arg):
        if not arg in [0,1,2,3,4]:
            return False
        else:
            return self.commandDevice(11, arg)

    @Commands.CommandMethod
    def saveSetpointAsStartup(self):
        return self.commandDevice(12, None)

    @Commands.CommandMethod
    def changeLoopAlgorithm(self, arg):
        if not arg in [1,2]:
            return False
        else:
            return self.commandDevice(13, arg)

    @Commands.CommandMethod
    def readPID(self, arg):
        if not arg in [0,1,2]:
            return False
        else:
            return self.commandDevice(14, arg)

    @Commands.CommandMethod
    def changeSlaveID(self, arg):
        if not arg < 247 and not arg > 0:
            return False
        else:
            return self.commandDevice(32767, arg)

    @Commands.CommandMethod
    def getStatus(self):
        """ A function that obtains the device status (address 1201-1202) from the Alicat.

        Returns
        -------
        tuple
            Least significant register followed by the most significant register.
        """
        statusMostRequest = self.pins["DEVICE_STATUS_MOST"]["read_buffers"]["request"]
        statusMostResponse = self.pins["DEVICE_STATUS_MOST"]["read_buffers"]["response"]
        statusLeastRequest = self.pins["DEVICE_STATUS_LEAST"]["read_buffers"]["request"]
        statusLeastResponse = self.pins["DEVICE_STATUS_LEAST"]["read_buffers"]["response"]
        self.modbus.sendData(statusLeastRequest)
        self.modbus.recvData(statusLeastResponse)
        self.modbus.sendData(statusMostRequest)
        self.modbus.recvData(statusMostResponse)
        leastFmt = self.modbus.DEVICE_ENDIAN + self.modbus.TYPE_MAP[self.pins["DEVICE_STATUS_LEAST"]["data_type"]]
        leastData = self.modbus.extractData(leastFmt, self.pins["DEVICE_STATUS_LEAST"]["read_buffers"]["response"])
        mostFmt = self.modbus.DEVICE_ENDIAN + self.modbus.TYPE_MAP[self.pins["DEVICE_STATUS_LEAST"]["data_type"]]
        mostData = self.modbus.extractData(mostFmt, self.pins["DEVICE_STATUS_MOST"]["read_buffers"]["response"])
        return (leastData, mostData)

    """
    Functions that the alicat uses to manage internal data.
    """

    def commandDevice(self, ID, argument):
        """ A Function that will send a command to the device over modbus. It will set register 1000 to the ID and 1001
        to the command argument (if supplied)

        Parameters
        ----------
        ID : int
            An integer between 1 and 14, or 32767.
        argument: int, None
            Range specific to command

        Returns
        -------
        str : parsed and interpreted status of the command
        """
        self.setCommandBuffer(ID, argument)
        deviceInstruction = self.pins["DEVICE_COMMAND"]["write_buffers"]["request"]
        deviceResponse = self.pins["DEVICE_COMMAND"]["write_buffers"]["response"]
        commandIDReq = self.pins["COMMAND_ID"]["read_buffers"]["request"]
        commandIDResp = self.pins["COMMAND_ID"]["read_buffers"]["response"]
        commandStatusReq = self.pins["COMMAND_STATUS"]["read_buffers"]["request"]
        commandStatusResp = self.pins["COMMAND_STATUS"]["read_buffers"]["response"]
        self.modbus.sendRecv(deviceInstruction, deviceResponse)
        self.modbus.sendRecv(commandIDReq, commandIDResp)
        self.modbus.sendRecv(commandStatusReq, commandStatusResp)
        lastCommandReturn = self.modbus.extractData(self.modbus.DEVICE_ENDIAN + self.modbus.TYPE_MAP[self.pins["COMMAND_STATUS"]["data_type"]], commandStatusResp)
        return self.parseCommandStatus(lastCommandReturn) if self.parseCommandStatus(lastCommandReturn) else lastCommandReturn

    def setCommandBuffer(self, ID, argument):
        """ A function that sets the internal command buffer to be sent over modbus to command the device.

        Parameters
        ----------
        ID : int
            An integer between 1 and 14, or 32767.
        argument: int
            Range specific to command

        Returns
        -------
        True if successful.
        """
        requestBuffer = self.pins["DEVICE_COMMAND"]["write_buffers"]["request"]
        dataTypes = []
        data = []
        dataTypes.append(self.pins["COMMAND_ID"]["data_type"])
        dataTypes.append(self.pins["COMMAND_ARGUMENT"]["data_type"])
        data.append(ID)
        data.append(argument)
        self.modbus.setWriteData(requestBuffer, data, dataTypes)
        return True

    def parseCommandStatus(self, commandStatus):
        """ A function that will return a string describing what the command status is.

        Parameters
        ----------
        commandStatus

        Returns
        -------
        bool, str
            The bool indicates success (True) or failure (False), and str describes the commandStatus.
        """
        if commandStatus == 0:
            return True, "Success!"
        if commandStatus >= 236 and commandStatus <= 255:
            return True, "Set Gas Mix Index {}".format(commandStatus)
        if commandStatus & 0x8000:
            error = commandStatus & 0xf
            if error == 1:
                # Invalid Command ID
                return False, "Invalid Command ID"
            elif error == 2:
                # invalid setting
                return False, "Invalid Setting"
            elif error == 3:
                # Request feature is unsupported
                return False, "Requested feature is unsupported"
            elif error == 4:
                return False, "Invalid gas mix index"
            elif error == 5:
                return False, "Invalid gas ix constituent"
            elif error == 6:
                return False, "Invalid gas mix percentage"
        return False, "Unknown Command Status: {}".format(commandStatus)


class ExternalCommands(Enum):
    increaseSetpoint = 0
    decreaseSetpoint = 1


ALICAT_COMMAND_MAP = {
    ExternalCommands.increaseSetpoint: AlicatMFCReader.increaseSetpoint,
    ExternalCommands.decreaseSetpoint: AlicatMFCReader.decreaseSetpoint
}

class DeviceCommands(Enum):
    changeGasNumber = 1
    mixGas = 2
    deleteGasMixture = 3
    tare = 4
    totalizerReset = 5
    valveSetting = 6
    displayLock = 7
    changeP = 8
    changeD = 9
    changeI = 10
    changeControlVar = 11
    saveCurrentSetpoint = 12
    changeControlAlg = 13
    readPID = 14
    changeModbusID = 32767

StatisticOutputs = ["MFC", "MFM", "PG", "PC"]

GasNumbers = {14: 'C2H2',
              0: 'Air',
              1: 'Ar',
              16: 'i-C4H10',
              13: 'n-C4H10',
              4: 'CO2',
              3: 'CO',
              60: 'D2',
              5: 'C2H6',
              15: 'C2H4',
              7: 'He',
              6: 'H2',
              17: 'Kr',
              2: 'CH4',
              10: 'Ne',
              8: 'N2',
              9: 'N2O',
              11: 'O2',
              12: 'C3H8',
              19: 'SF6',
              18: 'Xe',
              32: 'NH3',
              80: '1Butene',
              81: 'cButene',
              82: 'iButene',
              83: 'tButene',
              84: 'COS',
              33: 'Cl2',
              85: 'CH3OCH3',
              34: 'H2S',
              31: 'NF3',
              30: 'NO',
              36: 'C3H6',
              86: 'SiH4',
              35: 'SO2',
              100: 'R-11',
              101: 'R-115',
              102: 'R-116',
              103: 'R-124',
              104: 'R-125',
              105: 'R-134A',
              106: 'R-14',
              107: 'R142B',
              108: 'R-143A',
              109: 'R-152A',
              110: 'R-22',
              111: 'R-23',
              112: 'R-32',
              113: 'RC-318',
              114: 'R-404A',
              115: 'R-407C',
              116: 'R-410A',
              117: 'R-507A',
              23: 'C-2',
              22: 'C-8',
              21: 'C-10',
              140: 'C-15',
              141: 'C-20',
              20: 'C-25',
              142: 'C-50',
              24: 'C-75',
              25: 'He-25',
              143: 'He-50',
              26: 'He-75',
              144: 'He-90',
              27: 'A1025',
              28: 'Star29',
              145: 'Bio-5M',
              146: 'Bio-10M',
              147: 'Bio-15M',
              148: 'Bio-20M',
              149: 'Bio-25M',
              150: 'Bio-30M',
              151: 'Bio-35M',
              152: 'Bio-40M',
              153: 'Bio-45M',
              154: 'Bio-50M',
              155: 'Bio-55M',
              156: 'Bio-60M',
              157: 'Bio-65M',
              158: 'Bio-70M',
              159: 'Bio-75M',
              160: 'Bio-80M',
              161: 'Bio-85M',
              162: 'Bio-90M',
              163: 'Bio-95M',
              164: 'EAN-32',
              165: 'EAN',
              166: 'EAN-40',
              167: 'HeOx-20',
              168: 'HeOx-21',
              169: 'HeOx-30',
              170: 'HeOx-40',
              171: 'HeOx-50',
              172: 'HeOx-60',
              173: 'HeOx-80',
              174: 'HeOx-99',
              175: 'EA-40',
              176: 'EA-60',
              177: 'EA-80',
              178: 'Metabol',
              185: 'Syn Gas-1',
              186: 'Syn Gas-2',
              187: 'Syn Gas-3',
              188: 'Syn Gas-4',
              189: 'Nat Gas-1',
              190: 'Nat Gas-2',
              191: 'Nat Gas-3',
              192: 'Coal Gas',
              193: 'Endo',
              194: 'HHO',
              195: 'HD-5',
              196: 'HD-10',
              179: 'LG-4.5',
              180: 'LG-6',
              181: 'LG-7',
              182: 'LG-9',
              183: 'HeNe-9',
              184: 'LG-9.4',
              197: 'OCG-89',
              198: 'OCG-93',
              199: 'OCG-95',
              200: 'FG-1',
              201: 'FG-2',
              202: 'FG-3',
              203: 'FG-4',
              204: 'FG-5',
              205: 'FG-6',
              29: 'P-5',
              206: 'P-10'}
