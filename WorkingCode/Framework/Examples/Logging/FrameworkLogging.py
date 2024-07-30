import tempfile

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.Archive.Logger import LoggingReader
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.FrameworkObject import FrameworkObject


class ExampleFrameworkLogger(FrameworkObject):
    def emitLog(self, message):
        self.logger.debug(message)
        pass

    def _onExitCleanup(self):
        FrameworkObject._onExitCleanup(self)

    def start(self):
        FrameworkObject.start(self)

    def end(self):
        FrameworkObject.end(self)


exampleConfig = {
  "version": 1,
  "formatters": {
    "simple": {
        'format': "%(asctime)s | %(name)s | %(levelname)s \n\tMessage: %(message)s"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "DEBUG",
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
  }
}

def main():
    with tempfile.TemporaryDirectory() as tdir:
        with DirectoryArchiver(baseDir=tdir) as da:
            # all setup for the logging is inherent to the 'FrameworkObject' base class. Use 'self.logger'
            # to get the logger associated with that object.
            e0 = ExampleFrameworkLogger('Example Logger 0')
            e0.emitLog('This logger was made before the configuration of root occurred, and will not appear on console or in archive.')

            # sets up logging using exampleConfig. Once instantiated, will send all logs from root into the archive based on the name
            # of the emitting object.
            LoggingReader(da, None, None, None, logConfig=exampleConfig)
            e1 = ExampleFrameworkLogger('Example Logger 1')
            e1.emitLog('Emitting log from main() and will appear on the console and in archive.')
            print(da.read('Example Logger 1', channelType=ChannelType.Log))

if __name__ == '__main__':
    main()