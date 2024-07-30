import unittest

from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Package import Package
from Utils import Encoding as en
from Utils import EnumsEncoder as enEnc


class TestEncoding(unittest.TestCase):
    def test_jsonSerialize(self):
        simpleD = {
            'firstField': 1,
            'secondField': 2,
            'thirdField': [3],
            'fourthField': {'four': 4}
        }

        dumped = en.restrictedJSONDumps(simpleD)
        loaded = en.restrictedJSONLoads(dumped)

        try:
            self.assertEqual(simpleD, loaded)
        finally:
            pass

    def test_jsonSerializeWithEnums(self):
        enumDict = {"test": ChannelType.Data}
        dumped = en.restrictedJSONDumps(enumDict, encodeEnums=True)
        loaded = en.restrictedJSONLoads(dumped)
        self.assertEqual(enumDict, loaded)

    def test_jsonSerializeWithClassEncoding(self):
        enumDict = {"test": ChannelType.Data}
        dumped = en.restrictedJSONDumps(enumDict, encodeClasses=True)
        loaded = en.restrictedJSONLoads(dumped)
        self.assertEqual(enumDict, loaded)

    def test_jsonSerializeAsBytes(self):
        enumDict = {"test": ChannelType.Data}
        dumped = en.restrictedJSONDumps(enumDict, toBytes=True)
        loaded = en.restrictedJSONLoads(dumped)
        self.assertEqual(enumDict, loaded)

    def test_JsonSerializeWithAllEncoding(self):
        d = {"test": ChannelType.Data}
        p = Package(payload=d)
        packageDict = p.toDict()
        dumped = en.restrictedJSONDumps(packageDict, encodeClasses=True, encodeEnums=True, toBytes=True)
        loaded = en.restrictedJSONLoads(dumped)
        self.assertEqual(packageDict, loaded)

    def test_JsonSerializeWithSerialPayload(self):
        d = {"test": ChannelType.Data}
        serialD = en.restrictedJSONDumps(d)
        p = Package(payload=serialD)
        packageDict = p.toDict()
        dumped = en.restrictedJSONDumps(packageDict, encodeClasses=True, encodeEnums=True, toBytes=True)
        loaded = en.restrictedJSONLoads(dumped)
        self.assertEqual(packageDict, loaded)

    def test_enumEncoding(self):
        for enums in enEnc.ENUM_TYPES.keys():
            for e in enums:
                encoded = enEnc.encode(e)
                decoded = enEnc.decode(encoded)
                self.assertEqual(e, decoded)

