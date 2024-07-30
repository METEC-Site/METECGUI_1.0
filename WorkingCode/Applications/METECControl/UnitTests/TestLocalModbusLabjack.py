import os
import unittest

from Applications.METECControl.Readers.LabjackModbusServer import LocalModbusLabjack
from Framework.Archive.DirectoryArchiver import DirectoryArchiver


# Modbus = Modbus()

class TestModbus(unittest.TestCase):

    def test_init(self):
        archiver = DirectoryArchiver(baseDir="./", readonly=True, configFiles=[{'channel': 'LabJackPinsToRegisters','basePath': os.path.abspath("../Config"), 'subPath': 'labjack_config', 'fileName': 'pins_to_registers.csv'}])
        localMB = LocalModbusLabjack("LabJackPinsToRegisters", archiver)
        localMB.start()
        localMB.terminate = True