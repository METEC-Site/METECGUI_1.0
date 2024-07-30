from logging.handlers import QueueHandler

from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Package import Package

REGISTRY = {}

def getTPH(queue=None):
    return REGISTRY[queue]

class ThreadedPipeHandler(QueueHandler):
    def __init__(self, channel, pipe):
        self.channel = channel
        self.pipe = pipe
        REGISTRY[channel] = self
        QueueHandler.__init__(self, pipe.inputQ)

    def emit(self, record):
        msg = self.format(record)
        package = Package(source=self.channel, channelType=ChannelType.Log, payload={'message': msg})
        self.pipe.accept(package)

