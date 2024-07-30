import logging
import struct as s
import unittest

from Applications.METECControl.Readers.Modbus import Modbus
from Applications.METECControl.Readers.ModbusFormat import ModbusFormat


# Modbus = Modbus()

class TestModbus(unittest.TestCase):

    def testGetNumRegisters(self):
        MF = ModbusFormat()
        self.assertEqual(MF.getNumRegisters("UINT64"), 4)
        self.assertEqual(MF.getNumRegisters("Q"), 4)
        self.assertEqual(MF.getNumRegisters("INT64"), 4)
        self.assertEqual(MF.getNumRegisters("q"), 4)
        self.assertEqual(MF.getNumRegisters("FLOAT32"), 2)
        self.assertEqual(MF.getNumRegisters("f"), 2)
        self.assertEqual(MF.getNumRegisters("DOUBLE"), 4)
        self.assertEqual(MF.getNumRegisters("d"), 4)
        self.assertEqual(MF.getNumRegisters("UINT32"), 2)
        self.assertEqual(MF.getNumRegisters("I"), 2)
        self.assertEqual(MF.getNumRegisters("INT32"), 2)
        self.assertEqual(MF.getNumRegisters("i"), 2)
        self.assertEqual(MF.getNumRegisters("UINT16"), 1)
        self.assertEqual(MF.getNumRegisters("H"), 1)
        self.assertEqual(MF.getNumRegisters("INT16"), 1)
        self.assertEqual(MF.getNumRegisters("h"), 1)
        self.assertEqual(MF.getNumRegisters("UINT8"), 1)
        self.assertEqual(MF.getNumRegisters("B"), 1)
        self.assertEqual(MF.getNumRegisters("INT8"), 1)
        self.assertEqual(MF.getNumRegisters("b"), 1)
        self.assertEqual(MF.getNumRegisters("char"), 1)
        self.assertEqual(MF.getNumRegisters("c"), 1)

    def testExtractData_LabjackTestRegister(self):
        fakeModbus = Modbus('localhost', 500)
        baItems = [0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0x01, 0x03, 0x04, 0x00, 0x11, 0x22, 0x33]
        fullBA = bytearray(13)
        s.pack_into('bbbbbbbbbbbbb', fullBA, 0, *baItems)
        data = fakeModbus.extractData('bbbb', fullBA)
        expectedMapping = {
            0: 0x00,
            1: 0x11,
            2: 0x22,
            3: 0x33
        }
        failed = False
        for i in range(0, len(data)):
            try:
                self.assertEqual(expectedMapping[i], data[i])
            except Exception as e:
                logging.error(e)
                failed = True
        if failed:
            raise AssertionError(f'Data extracted from Modbus was not correct. Expected {"".join([str(i) for i in expectedMapping.values()])}, got {"".join([str(i) for i in data])}')
        i=-10




if __name__ == "__main__":
    unittest.main()