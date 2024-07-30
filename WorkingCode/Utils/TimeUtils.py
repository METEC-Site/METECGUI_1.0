"""
.. _time-utils:

#################
Time Utils Module
#################

:Authors: Aidan Duggan
:Date: May 23, 2019

A module with helpful utils for converting epoch to datetime (with timezone information) and vice versa.
"""


import logging
from datetime import datetime, timedelta
from enum import Enum, auto
from time import gmtime, strftime

import pytz
from Utils import ClassUtils as cu

GLOBAL_OFFSET = 0
MIN_EPOCH = float('-inf')
MAX_EPOCH = float('inf')

class FormatKeys(Enum):
    US = auto()
    USTZ = auto()
    USFileSafe = auto()
    USFileSafeTZ = auto()
    ISO8601 = auto()
    ISO8601TZ = auto()
    ISO8601simple = auto()
    ISO8601FileSafe = auto()
    ISO8601FileSafeTZ = auto()
    ExcelCSV = auto()
    ExcelCSVTZ = auto()
    ExcelCSVSeconds = auto()
    ExcelCSVTZSeconds = auto()
    FileSafe = auto()
    FileSafeTZ = auto()

# Note: TODO: Look into congress's changing Daylight Savings Time.
formats = {
    FormatKeys.US: '%m/%d/%Y %H:%M:%S',
    FormatKeys.USTZ: '%m/%d/%Y %H:%M:%S %Z%z',
    FormatKeys.USFileSafe: '%m-%d-%Y_%H-%M-%S',
    FormatKeys.USFileSafeTZ: '%m-%d-%Y_%H-%M-%S_%Z%z',
    FormatKeys.ISO8601simple: '%Y-%m-%d %H:%M:%S',
    FormatKeys.ISO8601: '%Y-%m-%d %H:%M:%S.%f',
    FormatKeys.ISO8601TZ: '%Y-%m-%d %H:%M:%S.%f %Z%z',
    FormatKeys.ISO8601FileSafe: '%Y-%m-%d_%H-%M-%S-%f',
    FormatKeys.ISO8601FileSafeTZ: '%Y-%m-%d_%H-%M-%S-%f_%Z%z',
    FormatKeys.ExcelCSV: '%m/%d/%Y %H:%M',
    FormatKeys.ExcelCSVTZ: '%m/%d/%Y %H:%M %Z%z',
    FormatKeys.ExcelCSVSeconds: '%m/%d/%Y %H:%M:%S',
    FormatKeys.ExcelCSVTZSeconds: '%m/%d/%Y %H:%M:%S %Z%z',
    FormatKeys.FileSafe: "%Y-%m-%d_%H.%M.%S",
    FormatKeys.FileSafeTZ: "%Y-%m-%d_%H.%M.%S_%Z%z"
}

EPOCH_BASE_AWARE = datetime(1970, 1, 1, tzinfo=pytz.utc)
EPOCH_BASE_NAIVE = datetime(1970, 1, 1)

def systemTZ():
    return strftime('%Z%z', gmtime())

def elapsedSeconds(ts1, ts2):
    """ returns the difference between two datetime/epoch time objects.

    .. _elapsed-seconds:

    :param ts1: Timestamp 1
    :param ts2: Timestamp 2.
    :type ts1: datetime, epoch time (float or int)
    :type ts2: datetime, epoch time (float or int)
    :return: diff between ts2 and ts1
    """
    if type(ts1) is datetime:
        ts1 = DTtoEpoch(ts1)
    if type(ts2) is datetime:
        ts2 = DTtoEpoch(ts2)
    return ts2-ts1

def displayLocal(dt, toTZ=None, fmt=formats[FormatKeys.FileSafe]):
    f"""Takes the timezone information of a datetime object and returns a local time in YMD HMS.
    
    If the dt object has a tzinfo field, this method will use that to convert output into local time. However, if toTZ is
    specified, then this method will ignore the dt.tzinfo (if it exists) and use the toTZ instead. If neither exist, then 
    the default timezone of UTC will be used, and displayed in terms of that. If a format is specified, this method will
    attempt to use that format unless it throws an error with datetime.strftime, in which case the default {formats[FormatKeys.FileSafe]}
    will be used. 
    
    .. notes::
        - If toTZ is not a real tz object nor exists within pytz.all_timezones, then UTC timezone will be used. 
        - is dt is Naive, then it is presumed to be of the system's local time zone. 
    
    :param dt: datetime (or epoch time) object to convert to local time
    :param toTZ: timezone information, used to convert datetime object if no tzinfo is attached to dt object.  
    :param fmt: defaults to {formats[FormatKeys.FileSafe]}. Will use this to format output datetime using datetim.strftime.
    :type dt: datetime or epoch time (float, int)
    :type toTZ: str in pytz.all_timezones or tzinfo object.
    :type fmt: str 
    :return: str, local datetime formatted according to fmt.
    """
    if not type(dt) is datetime:
       dt = EpochtoDT(dt, tz=toTZ)

    if dt.tzinfo and toTZ is None:
        localTZ = dt.tzinfo
    else:
        # local TZ will be UTC if toTZ isn't an expected timezone.
        localTZ = normalizeTZ(toTZ)

    dispTime = dt.astimezone(localTZ)
    try:
        retTime = dispTime.strftime(fmt)
    except Exception as e:
        logging.error(f'Unable to format datetime using {fmt}. Using default format {formats[FormatKeys.FileSafe]} instead')
        retTime = dispTime.strftime(fmt)
    return retTime

def DTtoEpoch(dt):
    """Converts date to epoch seconds."""
    if dt.tzinfo:
        eTime = (dt - EPOCH_BASE_AWARE).total_seconds() #Next line is wrong if taking into account tzinfo + dt.tzinfo._utcoffset.days*86400.0 + dt.tzinfo._utcoffset.seconds
    else:
        eTime = (dt - EPOCH_BASE_NAIVE).total_seconds()
    return eTime
    # old code. Updated to conform to time zone standards.
    # try:
    #     ret = (dt - EPOCH_BASE_NAIVE).total_seconds()
    # except TypeError:
    #     ret = (dt - EPOCH_BASE_AWARE).total_seconds()
    # return ret

def EpochtoDT(epoch, tz=None):
    """Converts epoch seconds to date.

    :param epoch: Time in Epoch. If in DateTime, will return DateTime.
    :param tz: """
    if type(epoch) is datetime:
        return epoch

    if epoch == MIN_EPOCH:
        return datetime.min
    elif epoch == MAX_EPOCH:
        return datetime.max
    else:
        ret = (EPOCH_BASE_AWARE + timedelta(seconds=epoch))
    if not ret.tzinfo:
        ret = ret.replace(tzinfo=pytz.UTC)
    localTZ = normalizeTZ(tz)
    ret = ret.astimezone(tz=localTZ)
    return ret

def nowEpoch():
    """Creates an epoch based timestamp of the time when it was called."""
    utcNow = datetime.utcnow()
    utcNow = utcNow.replace(tzinfo=pytz.UTC)
    ts = (utcNow - EPOCH_BASE_AWARE).total_seconds()
    return ts

def nowEpochGO():
    now = nowEpoch()
    nowOffset = now + GLOBAL_OFFSET
    return nowOffset

def nowDT(tz = pytz.UTC):
    newTZ = normalizeTZ(tz)
    return datetime.now(newTZ)

def normalizeTZ(tz=None):
    ### return a pytz object based on passed tz. If TZ is within pytz.all_timezones and is a string, or if it is already
    ### a pytz object, return that. Otherwise, return the default pytz.utc object.
    try:
        if tz in pytz.all_timezones:
            newTZ = pytz.timezone(tz)
        elif pytz.tzinfo.BaseTzInfo in cu.allBases(tz):
            # object is a timezone object from pytz.
            newTZ = tz
        elif tz is None:
            newTZ = pytz.utc
        elif tz == 'UTC':
            newTZ = pytz.utc
        else:
            raise TypeError(f'passed tz object \'{tz}\' is not a pytz timezone object nor is a recognized timezone string. '
                            f'Setting tz to UTC.')
        return newTZ
    except TypeError as e:
        logging.error(e)
    # fallthrough, return pytz.utc
    return pytz.utc

def dtToStr(dt, format=None):
    raiseError = False
    dtStr = ''
    if not type(dt) is datetime:
        raise ValueError(f'Argument {dt} passed as dt is not of type DateTime')
    if format in list(FormatKeys):
        dtStr = dt.strftime(formats[format])
    else:
        try:
            dtStr = dt.strftime(format)
            pass
        except:
            raiseError = True
            pass
    if not raiseError:
        return dtStr
    else:
        raise ValueError(f'Unable to format datetime {dt} to format {format}')

def strToDT(dtStr, format=None):
    raiseError = False
    dt = None
    if not type(dtStr) is str:
        raise ValueError(f'Argument {dtStr} passed as dtStr is not of type str')
    if not format:
        for singleFormat in formats.values():
            try:
                dt = datetime.strptime(dtStr, singleFormat)
                break
            except Exception as e:
                pass
        pass
    elif format in list(FormatKeys):
        dt = datetime.strptime(dtStr, formats[format])
        # use that format as key to lookup corresponding format within formats
    else:
        # try to parse the format as a string.
        try:
            dt = datetime.strptime(dtStr, format)
        except Exception as e:
            raiseError = True
    if not raiseError:
        return dt
    else:
        raise ValueError(f'Unable to parse datetime string {dtStr} using format {format}')

def dtToStrNormalTZ(dt):
    try:
        return dtToStr(dt, formats[FormatKeys.USFileSafeTZ])
    except ValueError:
        return dtToStr(dt)

def strToDTNormalTZ(dt):
    return strToDT(dt, formats[FormatKeys.USFileSafeTZ])

def isValidTZ(tz):
    if tz in pytz.all_timezones or pytz.tzinfo.BaseTzInfo in cu.allBases(tz):
        return True
    else:
        return False

def getGlobalOffset():
    global GLOBAL_OFFSET
    return GLOBAL_OFFSET

def setGlobalOffset(value):
    global GLOBAL_OFFSET
    GLOBAL_OFFSET = value