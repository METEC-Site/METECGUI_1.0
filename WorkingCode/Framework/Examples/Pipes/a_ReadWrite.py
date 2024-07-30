import time

class SimpleReader:
    def __init__(self, name=None):
        self.counter = 0
        self.name = name if name else "IntervalReader"

    def read(self):
        print("\n")
        print(self.counter)
        self.counter += 1
        return " ".join(["Hello World from", self.name])

class SimpleDestination:
    def __init__(self, name=None):
        self.name = name if name else "Writer"

    def accept(self, package):
        print("{} accepted package".format(self.name))
        print(package)

def main():
    reader = SimpleReader("IntervalReader")
    writer = SimpleDestination("Writer 1")
    while True:
        package = reader.read()
        writer.accept(package)
        time.sleep(1)

if __name__ == '__main__':
    main()