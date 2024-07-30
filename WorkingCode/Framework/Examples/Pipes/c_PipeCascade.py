from Examples.Pipes.a_ReadWrite import SimpleReader, SimpleDestination
from Examples.Pipes.b_SimpleReadPipe import SimpleReadPipe

class SimplePipe():
    def __init__(self, name=None, destination=None):
        self.name = name if name else "Simple Pipe"
        self.destination = destination

    #TODO: make the series of events more clear
    def accept(self, package):
        print("Sending package to {} from {}".format(self.destination.name, self.name))
        self.destination.accept(package)

    def setDestination(self, destination):
        self.destination = destination

def main():
    reader = SimpleReader()
    writer = SimpleDestination()
    readPipe = SimpleReadPipe()
    secondPipe = SimplePipe(destination=writer)
    readPipe.setDestination(secondPipe)
    readPipe.setSource(reader)
    readPipe.run()

if __name__ == "__main__":
    main()