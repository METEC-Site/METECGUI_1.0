import logging
from logging.config import dictConfig

exampleConfig = {
  "version": 1,
  "formatters": {
    "simple": {
        'format': "%(asctime)s | %(name)s | %(levelname)s \n\tMessage: %(message)s",
    },
    "consoleOutput": {
        'format': "This Message is from Console Output \n\tMessage: %(message)s",
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "DEBUG",
      "stream": "ext://sys.stdout",
      "formatter": "consoleOutput"
    }
  },
  "root": {
    "level": "DEBUG",
    "handlers": [
      "console"
    ]
  }
}

class ExampleLogger():
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger(name)

    def emitLog(self):
        self.logger.debug(f'Emitting debug log from {self.name}')
    pass

def main():
    # Logging BEFORE output set up will not result in any logs being output according to the format
    firstLogger = ExampleLogger('FirstLogger') # first logger inherits from root logger config at this point. IE before config.
    firstLogger.emitLog()
    # set up basic config using dictionary.
    dictConfig(exampleConfig)
    secondLogger = ExampleLogger('SecondLogger')
    thirdLogger = ExampleLogger('ThirdLogger')

    # first logger maintains its handler (IE None), while second/third emits to console (since they were created after
    # the root log was reconfigured.)
    firstLogger.emitLog()
    secondLogger.emitLog()
    thirdLogger.emitLog()



if __name__ == '__main__':
    main()