from queue import Queue
from threading import Thread

from Examples.Pipes.a_ReadWrite import SimpleReader, SimpleDestination


def main():
    reader = SimpleReader("IntervalReader 1")
    writer = SimpleDestination("Writer 1")
    readPipe = ReadPipe("Read Pipe", reader, writer, 1)
    readPipe.run()


class ReadPipe(Thread):
    def __init__(self, name=None, source=None, destination=None, interval = .5):
        super().__init__()
        self.name = name if name else "Threaded Pipe"
        self.source = source
        self.destination = destination
        self.interval = interval
        self.inputQ = Queue()

    def setSource(self, source):
        self.source = source

    def setDestination(self, destination):
        self.destination = destination

    def run(self):
        while True:
            package = self.source.read()
            self.destination.accept(package)