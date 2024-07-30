import json
import logging
from enum import Enum
from logging.config import dictConfig
from logging.handlers import QueueHandler

from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Package import Package
from Framework.BaseClasses.Worker import Worker

LOGGER = {'logger': None}

defaultConfig = {
  "version": 1,
  "formatters": {
    "simple": {
      "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "INFO",
      "stream": "ext://sys.stdout"
    },
    "archiveLogger": {
      "()": "Framework.Archive.Logger.getLogger",
      "level": "DEBUG"
    }
  },
  "root": {
    "level": "DEBUG",
    "handlers": [
      "console",
      "archiveLogger"
    ]
  },
  "disable_existing_loggers": False
}

def getLogger():
    return LOGGER['logger']

class LoggingReader(QueueHandler, Worker):
    # Note: For this to work, name must be the same name as the log channel name as defined in the logging json file.
    def __init__(self, archiver=None, commandManager=None, dataManager=None, eventManager=None,
                 name='archiveLogger', logConfigFilepath = None, **kwargs):
        # _name specified so as to work with Queue handler, whose name setter requres a self._name variable.
        self._name = None
        Worker.__init__(self, archiver=archiver, commandManager=commandManager, dataManager=dataManager, eventManager=eventManager, name=name)
        QueueHandler.__init__(self, self.inputQueue)
        # self.name = name
        self.frameworkName = name
        self.archiver=archiver
        self.dataManager = dataManager


        self.rootLogger = logging.getLogger()
        LOGGER['logger'] = self
        dConfig = defaultConfig
        if logConfigFilepath:
            with open(logConfigFilepath) as f:
                dConfig = json.load(f)
        dictConfig(dConfig)

    def emit(self, record):
        package = Package(source=record.name, channelType=ChannelType.Log, payload=record)
        self.archiver.accept(package)

    def handlePackage(self, package):
        self.emit(package.payload)

    def end(self):
        Worker.end(self)




class DebugLevels(Enum):
    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG