from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Commands import CommandLevels, CommandStatus
from Framework.BaseClasses.Events import EventTypes

"""
    TODO: 
    Use this encoding encoding for packages and payload types. The channel type/payload type/timestamp information should be located in the header
        and the payload should be trailing the header.
    Add unit tests for all such encodings/decodings. 
    
"""

"""
Serialized headers for packages:

|package type|  |Package ID|  |Channel Type|  |Channel Subtype|     ...     |Payload|
\x00            \x00          \x00            \x00                  ...     \x00...\x00

Things that need to be encoded:
package ID
timestamp
source (as a string)?
namespace (as string)?
payload - serialized to/from dictionary. Json Dumps/loads method, and serialize as enum.

"""


ENUM_TYPE_MASK = 0xF00
ENUM_VAL_MASK =  0x0FF
ENUM_VAL_OFFSET = 8

ENUM_TYPES = {
    CommandLevels: 0,
    CommandStatus: 1,
    ChannelType: 2,
    EventTypes: 3
}
# Another dict created from ENUM_TYPES with the keys and values swapped for decoding
REVERSE_ENUM_TYPES = {v:k for k, v in ENUM_TYPES.items()}


def isEncodable(val):
    """ checks if value is an enum that can be encoded by the class"""
    for enumType in ENUM_TYPES.keys():
        if val in enumType:
            return True
    else:
        return False


def encode(en):
    """ :return: a number that represents the enum given. Original enum can be retrieved with decode()"""
    if isEncodable(en):
        eType = en.__class__
        eTypeNum = ENUM_TYPES[eType]
        return (eTypeNum << ENUM_VAL_OFFSET) + en.value
    else:
        raise Exception("EnumEncoder cannot encode "+str(en))


def decode(num):
    """ :return: the original enum that was encoded to the integer value given as an argment.
        throws an Exception if the number is not valid.
    """
    try:
        eTypeNum = (ENUM_TYPE_MASK & num) >> ENUM_VAL_OFFSET
        eValNum = ENUM_VAL_MASK & num
        eType = REVERSE_ENUM_TYPES[eTypeNum]
        for e in eType.__members__.values():
            if e.value == eValNum:
                return e
    except KeyError:
        raise Exception("EnumEncoder cannot find enum with encoding "+str(num))

if __name__ == '__main__':
    print("Original:", ChannelType.Event)
    print("Encoded:", encode(ChannelType.Event))
    print("Decoded:", decode(encode(ChannelType.Event)))