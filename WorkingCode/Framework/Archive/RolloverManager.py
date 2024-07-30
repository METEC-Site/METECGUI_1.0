"""
.. _rollover-manager:
################
Rollover Manager
################

:Authors: Aidan Duggan, Jerry Duggan
:Date: April 25, 2019

A module containing the classes that detect if it is time for a directory to _rollover based on Time or Size based criteria.
See also :ref:'Directory Archiver <directory-archiver>'
"""
__docformat__ = 'reStructuredText'

from abc import ABC, abstractmethod

from Utils import FileUtils as fUtils
from Utils import TimeUtils as tu


# TODO: Come up with format template for size based _rollover. IE what happens if the _rollover directory already exists?
# Rollover manager should be in charge of the nam of the DA's current/new directory. Should it?

def RolloverManager(rolloverCriteria='time', currentDir=None, rolloverInterval=86400, dirStartTime=tu.nowEpoch(), *args, **kwargs):
    # Note: the kwarg 'rolloverCriteria' will dictate which manager is instantiated and used, based on the mapping in
    # RO_MANAGER_MAP. If the criteria is not found in the mapping, this factory will instantiate the default to be
    # a size based model at the size provided (or 10 MB, if not specified)
    roManager = RO_MANAGER_MAP.get(rolloverCriteria, SizeROManager)
    return roManager(currentDir, rolloverInterval, dirStartTime, *args, **kwargs)

class ROBase(ABC):
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def toDict(self):
        pass

    @abstractmethod
    def checkRollover(self):
        pass

    def setCurrentDir(self, currentDir):
        # if currentDir isn't none, then set the current dir to the passed value and update the timestamp.
        if currentDir is None:
            raise TypeError('currentDir argument cannot be None.')
        self.currentDir = currentDir

class TimeROManager(ROBase):
    def __init__(self, currentDir=None, rolloverInterval=86400, dirStartTime=tu.nowEpoch(), **kwargs):
        ROBase.__init__(self, **kwargs)
        self.currentDir = None
        if currentDir:
            self.setCurrentDir(currentDir)
        self.interval = rolloverInterval #interval in seconds, default is one day.
        self.dirStartTime = dirStartTime
        self.setCurrentDir(currentDir=self.currentDir)
        pass

    def toDict(self):
        return self.__dict__

    def checkRollover(self):
        # if the total time since the directory start time was set to now is greater than the set interval (or if there
        # isn't a current directory set), send the signal to _rollover.
        elapsedTime = tu.elapsedSeconds(self.dirStartTime, tu.nowEpoch())  # seconds in epoch time
        if elapsedTime > self.interval or not self.currentDir:
            return True
        return False

    def incrementTime(self, ts=None):
        if ts == None:
            ts = self.interval
        self.dirStartTime = self.dirStartTime + ts


class SizeROManager(ROBase):
    def __init__(self, currentDir = None, rolloverInterval=10000000, dirStartTime=tu.nowEpoch(), *args, **kwargs):
        ROBase.__init__(self, *args, **kwargs)
        self.currentDir = None
        if currentDir:
            self.setCurrentDir(currentDir)
        self.interval = rolloverInterval # interval in bytes, default size is 10 MB
        self.dirStartTime = dirStartTime

    def toDict(self):
        return self.__dict__

    def checkRollover(self):
        # If there isn't a current directory or the size of the current directory is larger than the interval, send the
        # signal to _rollover.
        if not self.currentDir:
            return True
        size = fUtils.getSize(self.currentDir)  # size in bytes
        if size > self.interval:
            return True
        return False


RO_MANAGER_MAP = {
    'size': SizeROManager,
    'time': TimeROManager
}
