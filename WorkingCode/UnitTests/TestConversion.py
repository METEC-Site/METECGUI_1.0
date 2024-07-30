import unittest
from logging import StreamHandler

import UnitTests.TestAll as TA
import Utils.Conversion as Conversion

press = Conversion.updatedConversionTable["pressure"]
PSIA = press["PSIA"]["abbr"]
PSIG = press["PSIG"]["abbr"]
Torr = press["Torr"]["abbr"]
Bar = press["Bar"]["abbr"]
ATM = press["Atm"]["abbr"]

temp = Conversion.updatedConversionTable["temperature"]
F = temp["F"]["abbr"]
C = temp["C"]["abbr"]
K = temp["K"]["abbr"]

logs = []
LOGGER = {'logger': None}

logDict = {
    "version": 1,
    "formatters": {
        "simple": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "stream": "ext://sys.stdout"
        },
        "testLogger": {
            "()": "UnitTests.TestConversion.redirectError",
            "level": "ERROR",
            "name": 'testLogger'
        }
    },
    "root": {
        "level": "DEBUG",
        "handlers": [
            "console",
            "testLogger"
        ]
    }
}

def getLogger():
    return LOGGER['logger']

def setLevel():
    return None

class redirectError(StreamHandler):
    def __init__(self, name):
        self._name = None
        self.name=name
        StreamHandler.__init__(self)
        # LOGGER['logger'] = self
        self.msgs = []
        logs.append('msg')

    def emit(self, record):
        message = self.format(record)
        print("MESSAGE RECEIVED", message)
        self.msgs.append(message)



class TestConversion(unittest.TestCase):

    @TA.CleanNamespace('test_TemperatureConversions')
    def test_TemperatureConversions(self):
        value = 33.8
        toCFromF = Conversion.convert(value, F, C)
        self.assertEqual(1, round(toCFromF, 2))
        toFFromC = Conversion.convert(toCFromF, C, F)
        self.assertEqual(value, round(toFFromC, 2))

        value = -459.67
        toKFromF = Conversion.convert(value, F, K)
        self.assertEqual(0, round(toKFromF, 2))
        toFFromK = Conversion.convert(toKFromF, K, F)
        self.assertEqual(value, round(toFFromK, 2))

        value = -273.15
        toKFromC = Conversion.convert(value, "C", "K")
        self.assertEqual(0, round(toKFromC, 2))
        toCFromK = Conversion.convert(toKFromC, "K", "C")
        self.assertEqual(value, round(toCFromK, 2))

    @TA.CleanNamespace('test_PressureConversions')
    def test_PressureConversions(self):
        value = 14.7
        toPSIGFromPSIA = Conversion.convert(value, PSIA, PSIG)
        self.assertEqual(0, round(toPSIGFromPSIA, 2))
        toPSIAFromPSIG = Conversion.convert(toPSIGFromPSIA, PSIG, PSIA)
        self.assertEqual(value, round(toPSIAFromPSIG, 2))

        value = 0.019336774741554538
        toTorrFromPSIA = Conversion.convert(value, PSIA, Torr)
        self.assertEqual(1, round(toTorrFromPSIA, 2))
        toPSIAFromTorr = Conversion.convert(value, Torr, PSIA)
        self.assertEqual(round(value, 1), round(toPSIAFromTorr, 1))

        value = 14.7
        toBarFromPSIA = Conversion.convert(value, PSIA, Bar)
        self.assertEqual(1.01, round(toBarFromPSIA, 2))
        toPSIAFromBar = Conversion.convert(toBarFromPSIA, Bar, PSIA)
        self.assertEqual(value, round(toPSIAFromBar, 2))

        toAtmFromPSIA = Conversion.convert(value, PSIA, ATM)
        self.assertEqual(1, round(toAtmFromPSIA, 2))
        toPSIAFromAtm = Conversion.convert(toAtmFromPSIA, ATM, PSIA)
        self.assertEqual(value, round(toPSIAFromAtm, 2))

        value = 0
        toTorrFromPSIG = Conversion.convert(value, PSIG, Torr)
        self.assertEqual(760, round(toTorrFromPSIG, 2))
        toPSIGFromTorr = Conversion.convert(toTorrFromPSIG, Torr, PSIG)
        self.assertEqual(value, toPSIGFromTorr)

        toBarFromPSIG = Conversion.convert(value, PSIG, Bar)
        self.assertEqual(1, toBarFromPSIG)
        toPSIGFromBar = Conversion.convert(toBarFromPSIG, Bar, PSIG)
        self.assertEqual(value, toPSIGFromBar)

        toAtmFromPSIG =  Conversion.convert(value, PSIG, ATM)
        self.assertEqual(1, toAtmFromPSIG)
        toPSIGFromAtm = Conversion.convert(toAtmFromPSIG, ATM, PSIG)
        self.assertEqual(value, toPSIGFromAtm)

        value = 751.0
        toBarFromTorr = Conversion.convert(value, Torr, Bar)
        self.assertEqual(1.0, round(toBarFromTorr, 2))
        toTorrFromBar = Conversion.convert(toBarFromTorr, Bar, Torr)
        self.assertEqual(value, toTorrFromBar)

        value = 761.0
        toATMFromTorr = Conversion.convert(value, Torr, ATM)
        self.assertEqual(1, round(toATMFromTorr, 2))
        toTorrFromAtm = Conversion.convert(toATMFromTorr, ATM, Torr)
        self.assertEqual(value, round(toTorrFromAtm, 2))

        value = 1.0
        toATMFromBar = Conversion.convert(value, Bar, ATM)
        self.assertEqual(0.99, round(toATMFromBar, 2))
        toBarFromATM = Conversion.convert(toATMFromBar, ATM, Bar)
        self.assertEqual(value, toBarFromATM)

    class writer(object):
        log = []

        def write(self, data):
            self.log.append(data)
            # print(self.log)

        def getLog(self):
            return self.log

    @TA.CleanNamespace('test_ConversionGetDict')
    def test_ConversionGetDict(self):
        test = Conversion.getDict(F)
        self.assertEqual(['temperature', temp], test)
