import abc
import threading

from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.FrameworkObject import FrameworkObject
from Framework.BaseClasses.Package import Package
from Framework.BaseClasses.Readers.Reader import Reader
from Utils import ClassUtils as cu


class StreamReader(Reader, FrameworkObject, abc.ABC):
    def __init__(self, name, dataManager, **kwargs):
        Reader.__init__(self, name, **kwargs)
        self.name = name
        self.SRTerminate = False
        self.SRLock = threading.RLock()
        if not cu.isDataManager(dataManager) and not dataManager is None:
            raise TypeError(f'Error in StreamReader named {self.name} '
                            f'expects dataManager of type DataManager or None, not'
                            f'{type(dataManager)}.')
        self.dataManager = dataManager
        self.streamReadThread = threading.Thread(target=self.continuousRead, daemon=True)

    # Method that needs to be overwritten. Inherited from Reader.
    # def getReaderMetadata(self, sourceName=None):
    #     pass

    # Method that needs to be overwritten. Inherited from Reader.
    # def read(self):
    #     pass

    def continuousRead(self):
        while not self.SRTerminate:
            with self.SRLock:
                data = self.read()
                md = self.getReaderMetadata()
                if cu.isDataManager(self.dataManager) and data:
                    pkg = Package(source=self.name, payload=data, channelType=ChannelType.Data, metadata=md)
                    self.dataManager.accept(pkg)


    def start(self):
        self.streamReadThread.start()

    def end(self):
        self.SRTerminate = True