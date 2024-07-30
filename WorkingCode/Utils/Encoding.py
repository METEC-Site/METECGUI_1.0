import base64
import io
import json
import logging
import pickle
import sys
from datetime import datetime

import Utils.EnumsEncoder as EnumsEnc
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Commands import CommandStatus, CommandLevels
from Framework.BaseClasses.Events import EventTypes
from Utils import ClassUtils as cu
from Utils import TimeUtils as tu

SAFE_MODULES = {
    '__main__',
    'Framework.Manager.ProxyPickler',
    'builtins',
    'Framework.BaseClasses.Package',
    'Framework.BaseClasses.Metadata',
    'Framework.BaseClasses.Commands',
    'Framework.BaseClasses.Channels'
}

SAFE_CLASSES = {
    'ProxyType',
    'ChannelType',
    'Package',
    "Metadata",
    'CommandPayload',
    'CommandLevels',
    'ResponsePayload',
    'ProxyPayload',
    'ProxyPayloadType',
    'dict',
    'list'
}

SAFE_ENUMS = {
    'ChannelType': ChannelType,
    'EventTypes': EventTypes,
    'CommandStatus': CommandStatus,
    'CommandLevels': CommandLevels
}

CLASS_CODES = {
    "b64": {
        "readable":  "(__b64Encoded__)",
        "code": "(b)"
    },
    "datetime": {
        "readable":  "(__datetime__)",
        "code": "(d)"
    },
    "enum": {
        "readable": "(__enum__)",
        "code": "(e)"
    }
}


def restrictedUnpickle(s):
    """Helper function analogous to pickle.loads()."""
    return SafeUnpickler(io.BytesIO(s)).load()

def restrictedJSONLoads(s, *args, **kwargs):
    """
    can take bytes or string, with enums encoded or not encoded.
    """
    if type(s) is io.TextIOWrapper:
        s = s.read()
    if type(s) is bytes or type(s) is bytearray:
        s = s.decode("utf-8")
    loaded = json.loads(s, object_hook=asEnum, *args, **kwargs)
    return loaded

def restrictedJSONLoad(s, *args, **kwargs):
    loaded = json.load(s, object_hook=asEnum, *args, **kwargs)
    return loaded

def restrictedJSONDump(s, file, *args, **kwargs):
    s = json.dumps(s, cls=SafeJson, *args, **kwargs)
    dumped = print(s, file=file)
    return dumped

def restrictedJSONDumps(s, toBytes=False, encodeClasses=False, encodeEnums=False, *args, **kwargs):
    dumped = json.dumps(s, cls=SafeJson, encodeClasses=encodeClasses, encodeEnums=encodeEnums, *args, **kwargs)
    if toBytes:
        return dumped.encode("utf-8")
    return dumped

def toBytes(data):
    return data.encode('utf-8')

def fromBytes(data):
    return data.decode("utf-8")

class SafeJson(json.JSONEncoder):
    def __init__(self, encodeClasses=False, encodeEnums=False, *args, **kwargs):
        json.JSONEncoder.__init__(self, *args, **kwargs)
        self.args = args
        self.kwargs = kwargs
        self.encodeEnums = encodeEnums
        self.classEncodeKey = "readable"
        if encodeClasses:
            self.classEncodeKey = "code"

    def default(self, obj):
        if type(obj) is dict:
            dct = {}
            for key, value in obj.items():
                dct[self.default(key)] = self.default(value)
            # return json.JSONEncoder().encode(dct)
            return dct
        if type(obj) is list:
            ret = []
            for item in obj:
                ret.append(self.default(item))
            return ret
        if type(obj) is datetime:  # datetime
            obj = CLASS_CODES['datetime'][self.classEncodeKey] + tu.dtToStrNormalTZ(obj)
        if type(obj) is bytes or type(obj) is bytearray: #B64
            encoded = base64.b64encode(obj)
            jSerable = encoded.decode('utf-8')
            obj = ''.join([CLASS_CODES['b64'][self.classEncodeKey], jSerable])
        if type(obj) is str:
            return obj
        if type(obj) in SAFE_ENUMS.values():
            code = CLASS_CODES['enum'][self.classEncodeKey]
            if self.encodeEnums and EnumsEnc.isEncodable(obj):
                return code + str(EnumsEnc.encode(obj))
            else:
                return code + str(obj)
        if type(obj) is type:
            return str(obj)
        if not obj:
            return obj
        # replaced by below code in the try except loop.
        # if cu.isChannelInfo(obj) or cu.isPayload(obj) or cu.isFormatter(obj) or cu.isRolloverManager(obj) or cu.isArchiver(obj) or cu.isMetadata(obj) or cu.isPackage(obj):
        #     d = obj.toDict()
        #     return self.default(d)
        try:
            if cu.isMetadata(obj):
                i = -10
            d = obj.toDict()
            return self.default(d)
        except Exception as e:
            if cu.isFrameworkObject(obj):
                logging.exception(e)
            pass
        return obj

    def encode(self, o):
        defaulted = self.default(o)
        encoded = json.JSONEncoder(*self.args, **self.kwargs).encode(defaulted)
        return encoded

def getTag(value):
    """
    Finds a tag at the start of a string and returns it.
    matches with any tag in 'readable' or 'code' of CLASS_CODES
    """
    for encodings in CLASS_CODES.values():
        if value.startswith(encodings['readable']):
            return encodings['readable']
        if value.startswith(encodings['code']):
            return encodings['code']
    return False

def decodeValue(value):
    """
    Takes a string with possible tags such as (__enum__) and converts the following
    string into the correct object
    """
    v = value
    if type(value) is str:
        tag = getTag(value)
        if tag in CLASS_CODES['enum'].values():
            val = value.replace(tag, '')
            if val.isdigit():
                v = EnumsEnc.decode(int(val))
            else:
                cls, val = val.split('.')
                v = getattr(SAFE_ENUMS[cls], val)
        if tag in CLASS_CODES['b64'].values():
            byteString = value.replace(tag, '')
            encoded = byteString.encode('utf-8')
            v = base64.b64decode(encoded)
        if tag in CLASS_CODES['datetime'].values():
            v = value.replace(tag, '')
            try:
                v = tu.strToDTNormalTZ(v)
            except ValueError:
                v = tu.strToDT(v)
    return v


def utf8ToB64(pkt):
    strPkt = str(pkt, encoding='utf-8')
    strPkt = strPkt.replace('(__b64Encoded__)', '')
    encoded = strPkt.encode('utf-8')
    return base64.b64decode(encoded)


# todo: don't encode in strings, encode in dictionaries with encoding as field instead.
def asEnum(s):
    i=-10
    if type(s) is str:
        s = decodeValue(s)
    if type(s) is dict:
        repl = {}
        for key, value in s.items():
            k, v = key, value
            if type(value) is dict:
                s[key] = asEnum(value)
            k = decodeValue(k)
            v = decodeValue(v)
            repl[k] = v
        s = repl
    if type(s) is list:
        lst = []
        for item in s:
            lst.append(asEnum(item))
        s = lst
    return s

class SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module in SAFE_MODULES and name in SAFE_CLASSES:
            return getattr(sys.modules[module], name)
        raise pickle.UnpicklingError("'{:s}.{:s} is forbidden".format(module, name))

def jsonDumps(s):
    return json.dumps(s)

def pickleDumps(s):
    return pickle.dumps(s)

if __name__ == '__main__':
    print(getTag("(__enum__)"))
    d = {"test": ChannelType.Data}
    rjd = restrictedJSONDumps(d)
    encoded = restrictedJSONDumps(d, encodeClasses=True, encodeEnums=True)
    asBytes = restrictedJSONDumps(d, toBytes=True, encodeEnums=True, encodeClasses=True)
    print("restricted dumps:", rjd)
    print("encoded dumps", encoded)
    print("bytes dumps", asBytes)
    print("restricted loads:", restrictedJSONLoads(rjd))
    print("enumsEncoded loads:", restrictedJSONLoads(encoded))
    print("bytes loads:", restrictedJSONLoads(asBytes))


