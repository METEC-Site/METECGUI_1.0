import csv
import logging
import pathlib
import socket
import threading

from Applications.METECControl.Readers.Modbus import Modbus as MB

LJ_REGISTERS_FILE = pathlib.Path(pathlib.Path(__file__).parent).joinpath("LJPins", "pins_to_registers.csv")
LJ_DIO_FILE       = pathlib.Path(pathlib.Path(__file__).parent).joinpath("LJPins", "pin_to_dio.csv")

class LocalModbusLabjack(threading.Thread):

    def __init__(self, archiver):
        threading.Thread.__init__(self)
        self.serverPort = 52362
        self.terminate = False
        self.server = None
        pinsToRegs = self.importPinConfig(LJ_REGISTERS_FILE)
        self.pinsConfig = {}
        for pin, pinInfo in pinsToRegs.items():
            self.pinsConfig[int(pinInfo['start_address'])] = pinInfo['data_type'],pinInfo['pin']

    def importPinConfig(self, configPath):
        cfg = {}
        with open(configPath) as cfgFile:
            dr = csv.DictReader(cfgFile)
            for line in dr:
                if 'start_address' in line:
                    line['start_address'] = int(line['start_address'])
                cfg[line['pin']] = line
        return cfg

    def run(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind(("localhost", self.serverPort))
        while not self.terminate:
            try:
                data, addr = self.server.recvfrom(12)
                if data[7] == 3:
                    self.readRegisters(data, addr)
                elif data[7] == 16:
                    self.server.sendto(MB.makeWriteResponseFromCommand(data), addr)
                else:
                    self.server.sendto(data, addr)
            except Exception as e:
                logging.debug(e)

    def readRegisters(self, command, addr):
        readResponse, startAddress, numRegisters = MB.makeReadResponseFromCommand(command)
        fmt, values = self._getDataFormatValues(startAddress, numRegisters)
        MB.addReadResponseData(readResponse, fmt, values)
        self.server.sendto(readResponse, addr)

    def _getDataFormatValues(self, startAddress, numRegisters):
        registerOffset = 0
        valueFormat = ">"
        values = []
        while registerOffset < numRegisters:
            formatString, pin = self.pinsConfig.get(startAddress+registerOffset)
            fmt, size = self._getFmt(formatString)
            values.append(self._getRandom(fmt, pin))
            valueFormat+=fmt
            registerOffset += size
        return valueFormat, values

    def _getFmt(self, formatString):
        if formatString:
            if formatString == "UINT16":
                return "h", 1 # 1 is number of bytes for UINT16
            if formatString == "UINT32":
                return "i", 2 # 2 is number of bytes for UINT32
            if formatString == "FLOAT32":
                return "f", 2
        else:
            return None, None

    def _getRandom(self, fmt, pin):
        # todo: return more realistic values
        if "DIO" in pin:
            return 255
        else:
            return 2
        # if fmt == 'f':
        #     return 2
        #     return random.random()
        # if fmt == 'I':
        #     return 2
        #     return random.randint(0, 1)
        # if fmt == 'i' or fmt == 'h':
        #     return 2
        #     return random.randint(-1, 1)
