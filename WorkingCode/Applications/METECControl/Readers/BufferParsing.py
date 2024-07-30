import struct as s
from binascii import hexlify

from Applications.METECControl.Readers import ModbusFormat


def parseBuffer(buffer, startAddress=0, response=True, endian = ">"):
    uid=s.unpack_from(endian + ModbusFormat.UID_FMT, buffer, ModbusFormat.UID_OFFSET)
    pid=s.unpack_from(endian + ModbusFormat.PID_FMT, buffer, ModbusFormat.PID_OFFSET)
    tid=s.unpack_from(endian + ModbusFormat.TID_FMT, buffer, ModbusFormat.TID_OFFSET)
    length=s.unpack_from(endian + ModbusFormat.LEN_FMT, buffer, ModbusFormat.LEN_OFFSET)
    func = s.unpack_from(endian + ModbusFormat.FUNC_FMT, buffer, ModbusFormat.FUNC_OFFSET)[0]

    data = {}
    address = None
    numreg = None
    if func == 3:
        if response:
            # Read Multiple Response
            i = ModbusFormat.RRESP_DATA_OFFSET
            while i < len(buffer):
                data[int(startAddress + (i - ModbusFormat.RRESP_DATA_OFFSET) / 2)] = hexlify(s.pack("{}H".format(endian), s.unpack_from("{}H".format(endian), buffer, i)[0]))
                i+=2
        else:
            # Read Multiple Command
            address=s.unpack_from(endian + ModbusFormat.RCOM_START_ADDR_FMT, buffer, ModbusFormat.RCOM_START_ADDR_OFFSET)[0]
            numreg=s.unpack_from(endian + ModbusFormat.RCOM_NUM_REG_FMT, buffer, ModbusFormat.RCOM_NUM_REG_OFFSET)[0]
    if func == 16:
        if not response:
            address = s.unpack_from(endian + ModbusFormat.WRESP_START_ADDR_FMT, buffer, ModbusFormat.WCOM_START_ADDR_OFFSET)[0]
            numreg = s.unpack_from(endian + ModbusFormat.WRESP_NUM_REG_FMT, buffer, ModbusFormat.WCOM_NUM_REG_OFFSET)[0]
            i = ModbusFormat.WCOM_DATA_OFFSET
            while i < len(buffer):
                data[int(address + (i - ModbusFormat.WCOM_DATA_OFFSET) / 2)] = hexlify(s.pack("{}H".format(endian), s.unpack_from("{}H".format(endian), buffer, i)[0]))
                i += 2
        else:
            address = s.unpack_from(endian + ModbusFormat.WRESP_START_ADDR_FMT, buffer, ModbusFormat.WRESP_START_ADDR_OFFSET)[0]
            numreg = s.unpack_from(endian + ModbusFormat.WRESP_NUM_REG_FMT, buffer, ModbusFormat.WRESP_NUM_REG_OFFSET)[0]
    parsed = {
        'uid': uid,
        'pid': pid,
        'tid': tid,
        'len': length,
        'func': func,
        'startAddress': address if address else startAddress,
        'numreg': numreg,
        'data': data
    }
    return parsed
