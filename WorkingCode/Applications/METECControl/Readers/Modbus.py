import logging
import socket
import struct as s
import threading

import Utils.Errors as Errors
from Applications.METECControl.Readers.ModbusFormat import ModbusFormat as MF


class Modbus(MF):
    """
    A class that sends, receives, and can interpret modbus commands to devices that use modbus.

    Methods
    ----------
    makeReadCommand(startAddr, numreg, tid=None, pid=None, uid=None, func=None)
        Generates a read command for a modbus device.
    makeReadResponse(numreg)
        Generates an empty read response for a modbus device with space allocated for the number of registers to read.
    makeWriteCommand(startAddr=0, numreg=0, data=None, dataTypes = None, tid=None, pid=None, uid=None)
        Generates a write command with the specified information
    makeWriteResponse()
        Generates an empty write response.
    setWriteData(buffer, data, dataTypes)
        Sets the consecutive data with specified types within the write command buffer
    extractData(format, buffer)
        Gets the data of the specified format from specified buffer. Expects that the buffer is a response to a read or
        write command.
    connect(closeCurrent=True)
        If closeCurrent is set to true, which >99% of the time it should be, close the current socket and open a new one
        as specified by self.connType
    disconnect()
        Close the current socket and set self.sock to None.
    sendRecv(sendBuffer, recvBuffer)
        Send the sendBuffer through a socket to the device, and receive the reponse into recvBuffer.
    sendData(sendBuffer, resetConnection=False)
        Send the sendBuffer through a socket to the device. If resetConnection is set to true, it will make a new socket
        after this has occurred.
    recvData(recvBuffer, resetConnection=False)
        Receive data from the current socket into the recvBuffer. If resetConnection is true, run disconnect() then reconnect()
    getHeader(buffer)
        Extract the header (7 bytes) from the specified buffer.
    setHeader(buffer, tid=None, pid=None, length=None, uid=None, func=None)
        Set the header of buffer with specified parameters
    replaceHeader(buffer, newHeader)
        Replace the header of buffer with newHeader.
    getTID(buffer)
        Obtain the TID from the specified buffer
    setTID(buffer, tid=None)
        set the TID on the specified buffer.
    getPID(buffer)
        Obtain the PID from the specified buffer
    setPID(buffer, pid=None)
        set the PID on the specified buffer.
    getLEN(buffer)
        Obtain the LEN from the specified buffer
    setLEN(buffer, LEN=None)
        set the LEN on the specified buffer.
    getUID(buffer)
        Obtain the UID from the specified buffer
    setUID(buffer, uid=None)
        set the UID on the specified buffer.
    getFUNC(buffer)
        Obtain the FUNC from the specified buffer
    setFUNC(buffer, func=None)
        set the FUNC on the specified buffer.
    getNumRegisters(type)
        returns the number of registers (16 bits or 2 bytes) it takes to contain a certain type.
        (IE 1 byte is 1 register, 2 bytes is 1 register, 3 bytes is 2 registers etc)

    """

    def __init__(self, IP, port, sock=None, connType=socket.SOCK_STREAM, timeout=.125, modbusEndian = ">", deviceEndian=">", maxReadReg = 125, name=None):
        """
        Instantiation. Sets the device specifications and runs the "connect" method.

        Parameters
        ----------
        IP : str
            Specifies the IP address of the device.
        port : int
            Specifies the expected port of the device.
        sock : socket
            The internet socket used to connect to the device. If none is provided, then the modbus will instantiate its own.
        connType : socket.[type]
            Specifies the connection type of the socket. Defaults to SOCK_STREAM (TCP) but could use SOCK_DGRAM (UDP) as well.
        timeout : float
            Specifies the timeout interval for sockets. (IE how long the socket will wait for a response). Defaults to .125 sec.
        modbusEndian : str
            Specifies modbus's expected endianness for commands. Defaults to ">" (big), but could use "<" (little).
        deviceEndian : str
            Specifies this device's expected endianness. Defaults to ">" (big) but could use "<" (little).
            Currently depreciated, and may be eliminated in the future.
        maxReadReg : int
            Specifies the maximum number of registers (max number of bytes / 2) allowed for a command. Defaults to 125
        name : str
            Specifies the name of the device.
        """
        self.name = name
        self.IP = IP
        self.port = port
        self.sock = sock if sock else socket.socket(socket.AF_INET, connType)
        # set maximum timeout to be 5 seconds for connection.
        if not timeout < 5:
            self.timeout = 5
        else:
            self.timeout = timeout
        self.sock.settimeout(self.timeout)
        self.connType = connType
        self.MODBUS_ENDIAN = modbusEndian
        self.DEVICE_ENDIAN = deviceEndian
        self.MAX_READ_REG = maxReadReg
        self.sock.settimeout(self.timeout)
        self.lock = threading.RLock()

    def makeReadCommand(self, startAddr, numreg, tid=None, pid=None, uid=None, func=None):
        """ A function that creates a read command for a modbus device.

        Parameters
        ----------
        startAddr: int
            The modbus address that a command will start at.
        numreg: int
            The number of registers this command will request from the modbus device.
        tid: int
            Transaction ID to set for this modbus request
        pid: int
            Product ID to set for this modbus request
        uid: int
            Unit ID to set for this modbus request
        func: int
            Function number to set for this request. Most modbus read commands are 3 or 4 for read input/holding registers

        Returns
        ----------
        A buffer (bytearray) of the compiled read command.
        """
        if not func:
            func = 3
        length = 6
        bigBuffer = bytearray(s.calcsize(self.HEADER_FMT) + s.calcsize(self.READ_COM_FMT))
        self.setHeader(bigBuffer, tid, pid, length, uid, func)
        s.pack_into(self.MODBUS_ENDIAN + self.RCOM_START_ADDR_FMT, bigBuffer, self.RCOM_START_ADDR_OFFSET, startAddr)
        s.pack_into(self.MODBUS_ENDIAN + self.RCOM_NUM_REG_FMT, bigBuffer, self.RCOM_NUM_REG_OFFSET, numreg)
        return bigBuffer

    def makeReadResponse(self, numreg):
        """ A function that creates a read response for a read command sent to a modbus device.

        Parameter
        ----------
        numreg: int
            The number of registers that are to be requested from the device.

        Return
        ----------
        An empty buffer (bytearray) of size of the header + response packet + 2*number of registers.
        """
        headerSize = s.calcsize(self.HEADER_FMT)
        packetSize = s.calcsize(self.READ_RESP_FMT)
        buffer = bytearray(headerSize + packetSize + 2*numreg)
        return buffer

    @staticmethod
    def makeReadResponseFromCommand(readCommand):
        startAddress, numRegs = s.unpack_from(">"+MF.READ_COM_FMT, readCommand, MF.RCOM_START_ADDR_OFFSET)
        readResponse = bytearray(readCommand[:s.calcsize(MF.HEADER_FMT)])+bytearray(1+numRegs*2)
        s.pack_into(MF.RRESP_NUM_REG_FMT, readResponse, MF.RRESP_NUM_REG_OFFSET, min(2*numRegs,255))
        s.pack_into(MF.LEN_FMT, readResponse, MF.LEN_OFFSET, len(readResponse)-6)
        return readResponse, startAddress, numRegs

    @staticmethod
    def addReadResponseData(readResponse, fmt, values):
        s.pack_into(fmt, readResponse, MF.RRESP_DATA_OFFSET, *values)

    @staticmethod
    def makeWriteResponseFromCommand(writeCommand):
        writeResponse = bytearray(writeCommand[:MF.WCOM_DOUBLE_OFFSET])
        s.pack_into(">"+MF.LEN_FMT, writeResponse, MF.LEN_OFFSET, len(writeResponse)-6)
        return writeResponse


    def makeWriteCommand(self, startAddr=0, numreg=0, data=None, dataTypes=None, tid=None, pid=None, uid=None):
        """ A function to create a write command for a modbus device.

        Parameters
        ----------
        startAddr: int
            The starting address for the modbus registers to write.
        numreg: int
            The number of registers that this write command will write.
        data: int or list of ints
            The data to write to the individual registers.
        dataTypes: str or list of strs
            The types of the above data.
        tid: int
            Transaction ID to set for this modbus request
        pid: int
            Product ID to set for this modbus request.
        uid: int
            Unit ID to set for this modbus request

        Return
        ----------
        A buffer (bytearray) of the compiled modbus request
        """
        func = 16
        size = 13+2*numreg
        buffer = bytearray(size)
        self.setHeader(buffer, func=func, length=7+2*numreg, tid=tid, pid=pid, uid=uid)
        s.pack_into(self.MODBUS_ENDIAN + self.WCOM_START_ADDR_FMT, buffer, self.WCOM_START_ADDR_OFFSET, startAddr)
        s.pack_into(self.MODBUS_ENDIAN + self.WCOM_NUM_REG_FMT, buffer, self.WCOM_NUM_REG_OFFSET, numreg)
        s.pack_into(self.MODBUS_ENDIAN + self.WCOM_DOUBLE_FMT, buffer, self.WCOM_DOUBLE_OFFSET, 2*numreg)
        if data:
            self.setWriteData(buffer, data, dataTypes)
        return buffer

    def makeWriteResponse(self):
        """ A function that creates a write response for a write command.

        Return
        ----------
        An empty buffer (bytearray) of the created write response."""
        return bytearray(s.calcsize(self.HEADER_FMT) + s.calcsize(self.WRESP_START_ADDR_FMT) + s.calcsize(self.WRESP_NUM_REG_FMT))

    def setWriteData(self, buffer, data, dataTypes):
        """ A function that will set the consecutive data bytes of a modbus buffer.

        Parameters
        ----------
        buffer: bytearray
            Buffer in which the data will be set (occurs in place)
        data: int, list, or float
            data bytes to set within the buffer (bytearray).
        dataTypes: str or list of strs. Must match the types within ModbusFormat.TYPE_MAP

        Return
        ----------
        True if this operation is successful
        False if this operation is unsuccessful
        TODO: specify the offset of the data?
        """
        try:
            fmt = self.DEVICE_ENDIAN
            if type(dataTypes) is list:
                for dataType in dataTypes:
                    fmt += self.TYPE_MAP[dataType]if dataType in list(self.TYPE_MAP.keys()) else dataType
            else:
                fmt += self.TYPE_MAP[dataTypes] if dataTypes in list(self.TYPE_MAP.keys()) else dataTypes
            if s.calcsize(fmt) + self.WCOM_DATA_OFFSET > len(buffer):
                raise Errors.BufferError
            if type(data) == list:
                s.pack_into(fmt, buffer, self.WCOM_DATA_OFFSET, *data)
            else:
                s.pack_into(fmt, buffer, self.WCOM_DATA_OFFSET, data)
        except Errors.BufferError:
            logging.exception(msg="Could not set data {} within buffer {}".format(data, buffer), exc_info=True)
            return False
        return True


    def extractData(self, format, buffer):
        """ A function to extract the data from the buffer received by a modbus response.

        Parameters
        ----------
        format: str
            The format (corresponding to struct typing) of the data to extract from the buffer
        buffer: bytearray
            A bytearray containing the response of a modbus command (or a write command itself), as well as its data.

        Return
        ----------
            The data contained in the buffer
            False if the bytearray buffer function isn't 3, 4, or 16 or if the unpacking fails.
        """
        header = s.unpack_from(self.DEVICE_ENDIAN + self.HEADER_FMT, buffer, 0)
        func = header[4]
        error = bytes([func & 0x1f])
        if error and not error == bytes([func]):
            # if there is an error (IE anything in the flags marked with 1 in the bytes 0x11100000)
            logging.exception(msg=f"{self.name} received a modbus error {error} from response packet {buffer}", exc_info=True)
            return False
        if func == 3 or func == 4:
            # 3 and 4 are read commands, for read holding (3) or read input (4) registers.
            data = s.unpack_from(format, buffer,  self.RRESP_DATA_OFFSET)
        elif func == 16:
            # function code 16 is write multiple holding registers.
            data = s.unpack_from(format, buffer,  self.WCOM_DATA_OFFSET)
        else:
            data = False
        return data

    """ 
    Functions for connecting, sending, and receiving data from the modbus device specified by the IP, port, and socket type. 
    """

    def connect(self):
        """ A function that opens a new socket connection for internet communication.

        :return: True if the modbus was able to connect. False if the operation failed and the modbus could not connect.
        """
        with self.lock:
            try:
                conn = self.sock.connect_ex((self.IP, self.port))
                if conn == 0:
                    # no errors, was able to connect properly.
                    return True
                elif conn == 10038:
                    # operation performed on something that isn't a socket. Create a new socket and try again on that.
                    self.sock = socket.socket(socket.AF_INET, self.connType)
                    self.sock.settimeout(self.timeout)
                    return self.connect()
                elif conn == 10056:
                    # already connected to socket
                    logging.debug(msg=f"Already connected to socket ({self.IP}:{self.port})", exc_info=True)
                    return True
                else:
                    logging.debug(f'Could not connect to socket {self.IP}:{self.port} due to error code: {conn}')
                    return False
            except socket.timeout:
                logging.debug(f"Could not connect to device {self.name} on IP:port ({self.IP}:{self.port}) "
                              f"within {self.timeout} seconds", exc_info=True)
                return False
            except OSError as error:
                if error.errno == 10056:
                    # already connected to socket.
                    logging.debug(msg=f"Already connected to socket ({self.IP}:{self.port})", exc_info=True)
                    return True

    def disconnect(self):
        """ A function that closes and removes the current socket

        :return: True if the socket shutdown correctly, False if the connection timed out. """
        with self.lock:
            try:
                if self.sock:
                    self.sock.shutdown(socket.SHUT_RDWR)
                    self.sock.close()
                    return True
            except socket.timeout:
                # Could not connect to socket to send the shutdown command.
                logging.exception(f"Could not disconnect from device {self.name}, IP:Port {':'.join([self.IP, str(self.port)])} within {self.timeout} seconds", exc_info=True)
                return False
            except OSError as e:
                if e.errno == 10038:
                    # operation attempted on something that was not a socket. Therefore socket already shut down.
                    return True
                else:
                    logging.exception(
                        f"Could not disconnect from device {self.name}, IP:Port {':'.join([self.IP, str(self.port)])} due to error {e}",
                        exc_info=True)
                    return False

    def sendRecv(self, sendBuffer, recvBuffer):
        """ A function to send a modbus command from sendBuffer and receive the response into the recvBuffer.

        :param sendBuffer: The buffer to be sent to the modbus device.
        :param recvBuffer:
        :type sendBuffer: bytearray

        :return: True if the data was sent and received, False if either send or receive didn't succeed."""
        sent = self.sendData(sendBuffer)
        recv = self.recvData(recvBuffer)
        if True and (sent and recv):
            return True
        return False


    def sendData(self, sendBuffer):
        """ Send a buffer over the socket to a modbus device.

        :param sendBuffer: The buffer to be sent over the socket to a modbus device.
        :type sendBuffer: bytearray

        :return: True if the operation succeeded and buffer was sent, False if the operation failed.
        """
        with self.lock:
            try:
                if self.connType == socket.SOCK_STREAM:
                    # TCP
                    self.sock.send(sendBuffer)
                elif self.connType == socket.SOCK_DGRAM:
                    # UDP
                    self.sock.sendto(sendBuffer, (self.IP, self.port))
            except Exception as e:
                logging.exception(msg=f"Unable to send buffer from {self.name} to IP:port "
                                      f"({self.IP}:{self.port}) due to exception {e}", exc_info=True)
                return False
            return True

    def recvData(self, recvBuffer):
        """ A function that receives a packet from a modbus device.

        :param recvBuffer: The buffer that will receive the modbus command (will be overwritten)
        :type recvBuffer: bytearray

        :return: True if operation succeeded, False if operation failed.
        """
        with self.lock:
            try:
                self.sock.recv_into(recvBuffer)
            except socket.timeout:
                return False
            except OSError as e:
                # logging.exception(f'Unable to receive buffer from modbus connection to IP:port ({self.IP}:{self.port})'
                #                   f' due to OSError {e})', exc_info=True)
                return False
            except Exception as e:
                # logging.exception(f"Modbus connection to ({self.IP}:{self.port}) unable to receive into buffer due to exception: {e}")
                return False
            return True

    """
    Functions for making, altering, and receiving information from the modbus header. 
    """
    def getHeader(self, buffer):
        if len(buffer) >= s.calcsize(self.MODBUS_ENDIAN + self.HEADER_FMT):
            return s.unpack_from(self.HEADER_FMT, buffer, 0)

    def setHeader(self, buffer, tid=None, pid=None, length=None, uid=None, func=None):
        try:
            self.setTID(buffer, tid)
            self.setPID(buffer, pid)
            self.setLEN(buffer, length)
            self.setUID(buffer, uid)
            self.setFUNC(buffer, func)
        except Errors.BufferError:
            logging.exception(msg="Could not set all or part of header", exc_info=True)
        return buffer

    def replaceHeader(self, buffer, newHeader):
        if len(buffer) >= s.calcsize(self.HEADER_FMT) and len(newHeader) == s.calcsize(self.HEADER_FMT):
            s.pack_into(self.MODBUS_ENDIAN + self.HEADER_FMT, buffer, newHeader, 0)
        else:
            logging.log(level=logging.DEBUG, msg="Buffer or header size does not match the expected length")
            raise Errors.BufferError

    def setTID(self, buffer, tid=None):
        if tid is None:
            tid = 0
        if len(buffer) >= s.calcsize(self.TID_FMT) + self.TID_OFFSET:
            s.pack_into(self.MODBUS_ENDIAN + self.TID_FMT, buffer, self.TID_OFFSET, tid)
            return True
        else:
            raise Errors.BufferError

    def getTID(self, buffer):
        if len(buffer) >= s.calcsize(self.TID_FMT) + self.TID_OFFSET:
            return s.unpack_from(self.MODBUS_ENDIAN + self.TID_FMT, buffer, self.TID_OFFSET)[0]
        else:
            raise Errors.BufferError

    def setPID(self, buffer, pid=None):
        if pid is None:
            pid = 0
        if len(buffer) >= s.calcsize(self.PID_FMT) + self.PID_OFFSET:
            s.pack_into(self.MODBUS_ENDIAN + self.PID_FMT, buffer, self.PID_OFFSET, pid)
            return True
        else:
            raise Errors.BufferError

    def getPID(self, buffer):
        if len(buffer) >= s.calcsize(self.PID_FMT) + self.PID_OFFSET:
            return s.unpack_from(self.MODBUS_ENDIAN + self.PID_FMT, buffer, self.PID_OFFSET)[0]
        else:
            raise Errors.BufferError

    def setLEN(self, buffer, length=None):
        if length is None:
            length = 6
        if len(buffer) >= s.calcsize(self.LEN_FMT) + self.LEN_OFFSET:
            s.pack_into(self.MODBUS_ENDIAN + self.LEN_FMT, buffer, self.LEN_OFFSET, length)
            return True

        else:
            raise Errors.BufferError

    def getLEN(self, buffer):
        if len(buffer) >= s.calcsize(self.LEN_FMT) + self.LEN_OFFSET:

            return s.unpack_from(self.MODBUS_ENDIAN + self.LEN_FMT, buffer, self.LEN_OFFSET)[0]
        else:
            raise Errors.BufferError

    def setUID(self, buffer, uid=None):
        if uid is None:
            uid = 1
        if len(buffer) >= s.calcsize(self.UID_FMT) + self.UID_OFFSET:
            s.pack_into(self.MODBUS_ENDIAN + self.UID_FMT, buffer, self.UID_OFFSET, uid)
            return True
        else:
            raise Errors.BufferError

    def getUID(self, buffer):
        if len(buffer) >= s.calcsize(self.UID_FMT) + self.UID_OFFSET:
            return s.unpack_from(self.MODBUS_ENDIAN + self.UID_FMT, buffer, self.UID_OFFSET)[0]
        else:
            raise Errors.BufferError

    def setFUNC(self,  buffer, func=None):
        if func is None:
            func = 3
        if len(buffer) >= s.calcsize(self.FUNC_FMT) + self.FUNC_OFFSET:
            s.pack_into(self.MODBUS_ENDIAN + self.FUNC_FMT, buffer, self.FUNC_OFFSET, func)
            return True
        else:
            raise Errors.BufferError

    def getFUNC(self, buffer):
        if len(buffer) >= s.calcsize(self.FUNC_FMT) + self.FUNC_OFFSET:
            return s.unpack_from(self.MODBUS_ENDIAN + self.FUNC_FMT, buffer, self.FUNC_OFFSET)[0]
        else:
            raise Errors.BufferError

    # Moved to ModbusFormat
    # def getNumRegisters(self, type):
    #     """ A function to calculate the number of registers it takes to encapsulate a given type.
    #
    #     Parameters
    #     -----------
    #     type: str
    #         The type parameter must exist within the ModbusFormat.TYPE_MAP.
    #
    #     Return
    #     ----------
    #     True if this function is successful
    #     False if this function fails
    #
    #     """
    #     try:
    #         if type in self.TYPE_MAP:
    #             type = self.TYPE_MAP[type]
    #         return int(math.ceil(s.calcsize(type)/2))
    #     except TypeError:
    #         logging.exception(msg="Expected type argument to be of the form of a string", exc_info=True)
    #         return False
    #     except:
    #         logging.exception(msg="Could not find listed type in type map", exc_info=True)
    #         return False