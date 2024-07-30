import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from threading import RLock

import dask.dataframe as dd
import pandas as pd
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Metadata import METADATA_TYPE_MAP, Metadata
from Utils import ClassUtils as cu, Encoding as enc, TimeUtils as tu
from Utils.TimeUtils import MIN_EPOCH, MAX_EPOCH

DEFAULT_IDXLIMIT = 100
# todo: get rid of index formatter and just use csv.

def isNew(path, mode):
    try:
        if mode == "w":
            return True
        with open(path, 'r') as f:
            contents = f.read()
            if contents == '':
                return True
        return not os.path.exists(path)
    except Exception as e:
        logging.debug(f'Tried to determine age of filepath {path} but could not due to error {e}')
        return False


IDX_METADATA = {'timestamp': 'float', 'offset': 'int', 'count': 'int'}

def toConverterVect(metadata):
    # TODO: assign a default if the value doesn't exist in the metadata keys vector
    mdKeys = metadata.keys()

    mdVals = list(map(lambda x: metadata[x], mdKeys))
    if cu.isMetadata(metadata):
        i=0
        typeList = []
        for key in mdKeys:
            val = mdVals[i]
            valType = val.get('type', 'string')
            try:
                typeMap = METADATA_TYPE_MAP[valType]
            except KeyError:
                typeMap = METADATA_TYPE_MAP['string']
            typeList.append(typeMap)
            i+=1
        return typeList
    else:
        return list(map(lambda x: METADATA_TYPE_MAP[x], mdVals))


# note: metadata is really only used for CSV formatter, to define the fields when writing.
class Formatter(ABC):

    @abstractmethod
    def __init__(self, name, channelType, metadata, channelIO, readOnly=False, timestamp=None, path=None):
        pass

    @abstractmethod
    def ext(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def writeRow(self, d):
        pass

    @abstractmethod
    def read(self, minTS=MIN_EPOCH, maxTS=MAX_EPOCH, path=None):
        pass

    @abstractmethod
    def delete(self):
        pass

    @abstractmethod
    def toDict(self):
        pass

    @abstractmethod
    def getPath(self):
        pass

    def setPath(self, path):
        self.path=path

    def importPath(self, channelIO, channelType, readOnly, timestamp, path=None):
        if path and os.path.exists(path):
            absPath = path
        elif cu.isChannelIO(channelIO):
            absPath = channelIO.newAbsolutePath(channelType, timestamp=timestamp, create=not (readOnly))
        else:
            absPath = None
        return absPath

class IndexedCSVFormatter(Formatter):
    def __init__(self, name, channelType, metadata, channelIO, idxLimit=DEFAULT_IDXLIMIT, readOnly = False, timestamp=None, path=None, idxCsvPath=None, **kwargs):
        self.name = name
        self.idxName = name + "Idx"
        self.handleMetadata(metadata)
        self.idxKeys = IDX_METADATA.keys()
        self.idxCoverterVect = toConverterVect(IDX_METADATA)
        self.idxCount = 0
        self.idxLimit = idxLimit
        self.channelIO = channelIO

        self.csvPath, self.idxPath = self.importPaths(channelType, timestamp, readOnly, path, idxCsvPath)
        self.lock = RLock()

        self.readOnly = readOnly

        if not self.readOnly:
            self.writeHeaders()

    def setPath(self, path):
        self.csvPath = path

    def importPaths(self, channelType, timestamp, readOnly, path=None, idxCsvPath=None):
        csvPath = self.importPath(self.channelIO, channelType, readOnly, timestamp, path)
        idxPath = self.importPath(self.channelIO, ChannelType.Index, readOnly, timestamp, idxCsvPath)
        return csvPath, idxPath

    def getPath(self):
        return self.csvPath

    def handleMetadata(self, metadata=None):
            if not type(metadata) is dict and not cu.isMetadata(metadata):
                # todo: log an exception?
                metadata = {}
            self.addedHeaderRows = {}
            normalizedMD = Metadata(**metadata)
            uniqueHeaderNames = {}
            for mdName, mdValues in normalizedMD.items():
                for singleItem in mdValues.keys():
                    if not singleItem in uniqueHeaderNames:
                        uniqueHeaderNames[singleItem]=True
            if 'fieldname' in uniqueHeaderNames:
                uniqueHeaderNames.pop('fieldname')
            self.addedHeaderRows = {}
            for singleHeaderName in uniqueHeaderNames:
                inputs = []
                for fieldName, fieldMD in normalizedMD.items():
                    headerMD = fieldMD.get(singleHeaderName,'')
                    inputs.append(headerMD)
                joinedHeaders = ','.join([str(i) for i in inputs])
                self.addedHeaderRows[singleHeaderName] = joinedHeaders

            self.metadata = normalizedMD
            self.csvKeys =  list(normalizedMD.keys())
            self.csvConverterVect = toConverterVect(self.metadata)

    def toDict(self):
        if cu.isMetadata(self.metadata):
            md = self.metadata.toDict()
        else:
            md = self.metadata
        d={
            'path': self.csvPath,
            'metadata': md,
        }
        return d

    def writeHeaders(self):
        with self.lock:
            if isNew(self.csvPath, "a") and not self.readOnly:
                with open(self.csvPath, "w") as csvFLO:
                    header = ",".join(self.csvKeys)
                    print(header, file=csvFLO)
                    for headerName, singleHeader in self.addedHeaderRows.items():
                        print(singleHeader, file=csvFLO)
            if isNew(self.idxPath, "a") and not self.readOnly:
                with open(self.idxPath, "w") as idxFLO:
                    header = ",".join(self.idxKeys)
                    print(header, file=idxFLO)

    def delete(self):
        with self.lock:
            if os.path.exists(self.csvPath) and not self.readOnly:
                os.remove(self.csvPath)
            if os.path.exists(self.csvPath) and not self.readOnly:
                os.remove(self.idxPath)

    def ext(self):
        return 'csv'

    def writeRow(self, d):
        with self.lock:
            if not self.readOnly:
                with open(self.csvPath, "a") as csvFLO:
                    prevOffset = csvFLO.tell()
                    keylist = list(self.csvKeys)
                    # TODO: Change this to work with partially complete data readings.
                    try:
                        if type(d) is list:
                            for singleRow in d:
                                self.writeRow(singleRow)
                        else:
                            row = ",".join(map(lambda x: str(d[x]), keylist))
                            print(row, file=csvFLO)
                            csvFLO.flush()
                    except Exception as e:
                        logging.debug("Error in CSV Indexer writerow: {}. "
                                      "\n\trow to write: {}".format(e, d))

                self.idxCount += 1
                if (self.idxCount % self.idxLimit) == 0:
                    idxDat = {'timestamp': d['timestamp'], 'offset': prevOffset, 'count': self.idxCount}
                    row = ",".join(map(lambda x: str(idxDat[x]), self.idxKeys))
                    with open(self.idxPath, "a") as idxFLO:
                        print(row, file=idxFLO)
                        idxFLO.flush()
                    logging.debug("channel: {}, index record: {}".format(self.name, row))

    def close(self):
        pass

    def _trimHeaders(self, sFile):
        firstRow = sFile.readline()
        removeRows = []
        for fieldName, savedHeaderRow in self.addedHeaderRows.items():
            removeRows.append(sFile.readline())
        return firstRow, removeRows

    def read(self, minTS=MIN_EPOCH, maxTS=MAX_EPOCH, path=None, asDF=False, asDask=False):
        with self.lock:
            if not path:
                csvPath = self.csvPath
            else:
                csvPath = path
            if not os.path.exists(csvPath):
                return []

            if asDF or asDask:
                i=1
                for fieldName, savedHeaderRow in self.addedHeaderRows.items():
                    i+=1
                l = [i for i in range(1,i+1)]
                if asDF:
                    df = pd.read_csv(csvPath, skiprows=l)
                    return df
                if asDask:
                    # df = dd.read_csv(csvPath, skiprows=l)
                    df = dd.read_csv(csvPath, skiprows=l, sample=8192000) # added to try to get around following issue:
                    # ValueError: Mismatched dtypes found in `pd.read_csv`/`pd.read_table`. Seems that increasing sample size helps.
                    return df
            else:
                with open(csvPath, "r") as sFile:
                    retList = []

                    # remove the first row, the 'header'
                    row, additionalHeaders = self._trimHeaders(sFile)
                    header = list(row.strip().split(','))

                    # get a csv vector that can read from any file passed to it.
                    normMD = Metadata(**self.metadata)
                    for singleItem in header:
                        if not singleItem in normMD.keys():
                            normMD[singleItem] = {'type':str} # default reading is string if there is no more information.
                    # for singleName, md in self.metadata.items():
                    #     if not singleName in header:
                    #         normMD.pop(singleName)
                    csvKeys = normMD.keys()
                    csvConverterVect = toConverterVect(normMD)

                    row = sFile.readline() # get the first non header row.
                    while row:
                        fields = row.strip().split(',')
                        try:
                            if len(fields) == len(csvKeys):
                                combined = dict(zip(header, fields))
                                orderedFields = list(combined.get(csvKey,'') for csvKey in csvKeys)
                                outRow = dict(zip(csvKeys, map(lambda x: x[0](x[1]), zip(csvConverterVect, orderedFields))))
                                ts = outRow['timestamp']
                                if ts < minTS:
                                    pass
                                elif ts > maxTS:
                                    break
                                else:
                                    retList.append(outRow)
                                # TODO: Speak with code writer about intent of the following lines of code.
                            # if not path:
                            #     outRow = dict(zip(self.csvKeys, map(lambda x: x[0](x[1]), zip(self.csvConverterVect, fields))))
                            #     ts = outRow['timestamp']
                            #     if ts < minTS:
                            #         continue
                            #     if ts > maxTS:
                            #         break
                            # else:
                            #     outRow = dict(zip(header, fields))
                        except ValueError as e:
                            # line is missing fields (IE trying to convert empty string to float/int/etc).
                            logging.exception(e)
                            pass
                        except Exception as e:
                            logging.exception(e)
                        row = sFile.readline()
                return retList


class NullFormatter(Formatter):
    def __init__(self, name, channelType, metadata, channelIO, readOnly = False, timestamp=None, path=None):
        self.metadata = metadata
        self.lock = RLock()
        self.readOnly = readOnly
        self.channelIO = channelIO
        self.path = self.importPath(self.channelIO, channelType, readOnly, timestamp, path)

    def toDict(self):
        if cu.isMetadata(self.metadata):
            md = self.metadata.toDict()
        else:
            md = self.metadata
        d = {
            'metadata': md,
            'path': self.path
        }
        return d

    def getPath(self):
        return self.path

    def ext(self):
        return self.ext

    def writeRow(self, d, newline=''):
        with self.lock:
            if not self.readOnly:
                with open(self.path, "a") as flo:
                    print(d, file=flo, end=newline)

    def delete(self):
        with self.lock:
            if not self.readOnly:
                if os.path.exists(self.path):
                    os.remove(self.path)

    def close(self):
        pass

    def read(self, minTS=MIN_EPOCH, maxTS=MAX_EPOCH, path=None):
        with self.lock:
            if not path:
                path = self.path
            if os.path.exists(path):
                with open(path, 'r') as flo:
                    return flo.read()


class LoggerFormatter(NullFormatter):

    def __init__(self, name, channelType, metadata, channelIO, readOnly = False, timestamp=None, path=None):
        NullFormatter.__init__(self, name, channelType, metadata, channelIO, readOnly=readOnly, timestamp=timestamp, path=path)

    def writeRow(self, d, newline='\n'):
        if not self.readOnly:
            # todo: put formatting in the logger formatter json instead of here.
            dt = tu.EpochtoDT(d.created)
            dtStr = dt.strftime("%Y-%m-%d %H:%M:%S %z:%Z")
            logLine = f"\n{dtStr} | {d.levelname} | {d.threadName} | {d.msg}"
            NullFormatter.writeRow(self, logLine, newline=newline)


class JSONFormatter(Formatter):
    # JSON formatter rewrites the file every time. It will then prettify the output of the file. The read method
    # also ignores min/max ts.
    def __init__(self, name, channelType, metadata, channelIO, readOnly = False, timestamp=None, path=None):
        self.channelIO = channelIO
        self.path = self.importPath(self.channelIO, channelType, readOnly, timestamp, path)
        self.metadata = metadata
        self.lock=RLock()
        self.readOnly = readOnly

    def getPath(self):
        return self.path

    def toDict(self):
        if cu.isMetadata(self.metadata):
            md = self.metadata.toDict()
        else:
            md = self.metadata
        d = {
            "metadata": md,
            "path": self.path
        }
        return d

    def ext(self):
        return self.ext

    def writeRow(self, d):
        with self.lock:
            if not self.readOnly:
                with open(self.path, "w", newline="") as flo:
                    enc.restrictedJSONDump(d, flo, indent=4)

    def close(self):
        pass

    def delete(self):
        with self.lock:
            if not self.readOnly:
                if os.path.exists(self.path):
                    os.remove(self.path)

    def read(self, minTS=MIN_EPOCH, maxTS=MAX_EPOCH, path=None):
        with self.lock:
            if not path:
                path = self.path
            if os.path.exists(path):
                with open(path, "r") as flo:
                    try:
                        pls = enc.restrictedJSONLoad(flo)
                        return pls
                    except Exception as e:
                        logging.error(f'Could not read from file {path} due to exception : {e}')
                        return None
            return None

class LineJSONFormatter(JSONFormatter):
    # Line formatter will write an object to a json file line by line, unprettyfied, and will save it with a corresponding
    # timestamp. restrictedJSONLoad/dump will honor the enums found in the Utils.Encoding SAFE_ENUMS dict.
    # TODO: Expand this functionality to handle other types of enums (dynamically?)
    def __init__(self, name, channelType, metadata, channelIO, readOnly=False, timestamp=None, path=None):
        JSONFormatter.__init__(self, name, channelType, metadata, channelIO, readOnly=readOnly, timestamp=timestamp, path=path)

    def writeRow(self, j, ts=None):
        with self.lock:
            if not self.readOnly:
                if not type(ts) is float:
                    if type(ts) is datetime:
                        ts = tu.DTtoEpoch(ts)
                    else:
                        ts = tu.nowEpoch()
                tsDict = {'ts':ts, 'j':j}
                with open(self.path, 'a', newline='') as flo:
                    enc.restrictedJSONDump(tsDict, flo)

    def read(self, minTS=MIN_EPOCH, maxTS=MAX_EPOCH, path=None):
        # TODO: Honor mints/maxts. Maybe not read all the lines?
        # TODO: Think about returning a generator object for streaming type DATA
        with self.lock:
            if not path:
                path = self.path
            if os.path.exists(path):
                with open(path, 'r', newline='') as flo:
                    lines = flo.readlines()
                    corrLines = []
                    for line in lines:
                        tsDict = enc.restrictedJSONLoads(line)
                        ts = tsDict['ts']
                        j = tsDict['j']
                        if minTS <= ts and maxTS >= ts:
                            corrLines.append(j)
                    return corrLines
            return None