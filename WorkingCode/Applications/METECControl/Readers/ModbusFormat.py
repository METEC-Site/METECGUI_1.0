import logging
import math
import struct as s


class ModbusFormat():
    """Class that contains necessary formatting information for modbus commands and communication

    Attributes
    ----------
    TYPE_MAP : Dictionary
        A lookup table corresponding types to their struct formatting counterpart.
    Information Offsets : int
        Each offset corresponds to that specific information's offset within a bytearray
    Information Format : str
        Each format depicts the expected type (int8, uint16, etc) expected at that position.
        Example: The TID it expected to have H (UINT16) type (2 bytes), and will be located at an offset 2 bytes from
        the beginning of the bytearray.
    """

    TYPE_MAP = {
        "char":   "c",
        "INT8":   "b",
        "UINT8":  "B",
        "INT16":  "h",
        "UINT16": "H",
        "INT32":  "i",
        "UINT32": "I",
        "INT64":  "q",
        "UINT64": "Q",
        "FLOAT32":"f",
        "DOUBLE": "d"
        # what to do about strings???
    }

    HEADER_FMT = "HHHBB"
    READ_COM_FMT = "HH"
    READ_RESP_FMT = "B"
    WRITE_COM_FMT = "HHB"
    WRITE_RESP_FMT = "HB"

    ## Header format information
    TID_FMT = "H"
    TID_OFFSET = 0
    PID_FMT = "H"
    PID_OFFSET = 2
    LEN_FMT = "H"
    LEN_OFFSET = 4
    UID_FMT = "B"
    UID_OFFSET = 6
    FUNC_FMT = "B"
    FUNC_OFFSET = 7

    ## Read Request Command format information
    RCOM_START_ADDR_FMT = "H"
    RCOM_START_ADDR_OFFSET = 8
    RCOM_NUM_REG_FMT = "H"
    RCOM_NUM_REG_OFFSET = 10

    ## Read Request Response format information
    RRESP_NUM_REG_FMT = "B"
    RRESP_NUM_REG_OFFSET = 8
    RRESP_DATA_OFFSET = 9

    ## Write Request Command format information
    WCOM_START_ADDR_FMT = "H"
    WCOM_START_ADDR_OFFSET = 8
    WCOM_NUM_REG_FMT = "H"
    WCOM_NUM_REG_OFFSET = 10
    WCOM_DOUBLE_FMT = "B"
    WCOM_DOUBLE_OFFSET = 12
    WCOM_DATA_OFFSET = 13

    WRESP_START_ADDR_FMT = "H"
    WRESP_START_ADDR_OFFSET = 8
    WRESP_NUM_REG_FMT = "H"
    WRESP_NUM_REG_OFFSET = 10

    @staticmethod
    def getNumRegisters(dataType):
        """ A function to calculate the number of registers it takes to encapsulate a given type.

        Parameters
        -----------
        type: str
            The type parameter must exist within the ModbusFormat.TYPE_MAP.

        Return
        ----------
        True if this function is successful
        False if this function fails

        """
        try:
            if dataType in ModbusFormat.TYPE_MAP:
                dataType = ModbusFormat.TYPE_MAP[dataType]
            return int(math.ceil(s.calcsize(dataType)/2))
        except TypeError:
            logging.exception(msg="Expected type argument to be of the form of a string", exc_info=True)
            return False
        except:
            logging.exception(msg="Could not find listed type in type map", exc_info=True)
            return False
