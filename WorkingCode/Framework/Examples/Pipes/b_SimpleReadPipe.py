import time

from Examples.Pipes.a_ReadWrite import SimpleReader, SimpleDestination


class SimpleReadPipe:
    def __init__(self, name=None, source=None, destination=None, interval=1):
        self.name = name if name else "Read Pipe"
        self.source = source
        self.destination = destination
        self.interval = interval

    def setSource(self, source):
        self.source = source

    def setDestination(self, destination):
        self.destination = destination

    def run(self):
        while True:
            print("Sending data from {} to {} via {}".format(self.source.name, self.destination.name, self.name))
            package = self.source.read()
            self.destination.accept(package)
            time.sleep(self.interval)


def main():
    reader = SimpleReader()
    writer = SimpleDestination()
    pipe = SimpleReadPipe(source=reader, destination=writer)
    pipe.run()

if __name__ == '__main__':
    main()
