import logging

from Framework.BaseClasses.Readers.Reader import Reader
from Framework.Pipes.ReadPipe import ReadPipe as rp
from Utils import ClassUtils as cu


class IntervalReader(Reader):
    def __init__(self, name, dataManager=None, readPipe=None, readInterval=1, **kwargs):
        Reader.__init__(self, name=name, **kwargs)
        if not cu.isDataManager(dataManager) and not dataManager is None:
            raise TypeError(f'Interval reader named {self.getName()} expects dataManager to be of type DataManager or None, not'
                            f'{type(dataManager)}.')
        self.dataManager = dataManager
        if cu.isReadPipe(readPipe):
            self.readPipe = readPipe
        else:
            self._setupReadPipe(readPipe, readInterval, self.dataManager)
        self.readInterval = readInterval

    def _setupReadPipe(self, readpipe=None, readInterval=1, destination=None):
        if cu.isReadPipe(readpipe):
            self.readPipe = readpipe
        else:
            self.readPipe = rp(self.getName() + '-ReadPipe', source=self, destination=destination, freq=readInterval)

    def start(self):
        self._setupReadPipe(self.readPipe, self.readInterval, self.dataManager)
        if cu.isReadPipe(self.readPipe):
            self.readPipe.start()
        else:
            logging.warning(f'Unable to start Reader {self.getName()}; readPipe could not be created.')

    def end(self):
        self.readPipe.end()

    def getReaderMetadata(self, sourceName=None):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError