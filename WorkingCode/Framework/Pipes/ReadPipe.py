import logging
import time
from threading import Thread

from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Destination import ThreadedDestination
from Framework.BaseClasses.Package import Package
from Utils import ClassUtils as cu


class ReadPipe(ThreadedDestination):
    """ This is the main pipe that will interface with a reader. It calls read() every [interval] seconds, and sends that reading (in a package)
    to the destination specified in the __init__ or by setDestination.

    For this read pipe to work properly, destination must be a Destination and source must be a reader (have a 'read' method).

    Calling start on this read pipe will enter it into threaded mode. The runReading() method will run until end() is called,
    in which case terminate will be set to True and the runReading will end.

    Additionally, this class is a Destination, which means it inherits Destination.run(). This run() method will take packages
    off of the incoming inputQueue which have been added by the accept() method in the base class of Destination. It will
    call handlePackage on that package, which means that this read pipe will take that package and forward it to the same destination
    as the read() packages.

    'Source' and 'Destination' must be a 'Reader' and 'Destination' subclass respectively  for proper functionality,
    and the start() method must be executed after instantiation for the run and runReading() methods to run in their own threads."""
    insts = 0
    def __init__(self, name=None, source=None, destination=None, freq=1, **kwargs):
        name = name if name else "ReadPipe_{}".format(ReadPipe.insts)
        ThreadedDestination.__init__(self, name=name)
        ReadPipe.insts += 1
        self.destination = None
        self.source = None
        sourceSet = self.setSource(source)
        destSet = self.setDestination(destination)
        self.freq = freq
        self.terminate = False
        self.readThread = Thread(target=self.runReading, name=''.join([self.getName(), '_readThread']))

    def handlePackage(self, package):
        """ A method that is called by the base class Destination. Will forward any incoming packages on to destination.

        :param package:
        :return:
        """
        try:
            self.destination.accept(package)
        except Exception as e:
            logging.error(f'Read Pipe named {self.getName()} could not send package to destination {self.destination} due to '
                          f'following error: \n {e}')

    def setDestination(self, destination):
        if cu.isDestination(destination):
            self.destination = destination
            return True
        else:
            # logging.error(f'Could not set destination for read pipe named \'{# self.name}\' for the following reason:\n'
                          # f'destination {destination} is not of type Destination.')
            return False

    def setSource(self, source):
        """ Checks if the specified source is a reader. If it isn't, """
        if cu.isReader(source):
            self.source = source
            return True
        else:
            # logging.error(f"Read Pipe {self.name} is unable to set the source to {source} as this object is not a Reader")
            return False

    def read(self):
        """Wrapper for the source.read() method that does the packaging of read payload and sending of that to the destination.

        :return:
        """
        # Proposed alternate functionality #
        # if not self.terminate:
        #     self.sched.enter(self.freq, 1, self.read)
        # else:
        #     return False
        # End Proposed alternate functionality #
        if not self.source or not self.destination:
            return False
        try:
            payload = self.source.read()
            if payload is list:
                for singlePayload in payload:
                    package = Package(source=self.source.getName(), channelType=ChannelType.Data, payload=singlePayload)
                    self.destination.accept(package)
            elif payload:
                package = Package(source=self.source.getName(), channelType=ChannelType.Data, payload=payload)
                self.destination.accept(package)
            else:
                pass
            return payload
        except Exception as e:
            logging.error(e)

    def runReading(self):
        """Main target of the read thread. Runs read() on an interval continuously until

        While running, the ReadPipe will read data from the source (an IntervalReader) and wrap it in a custom Package class.
        Wait for a time, then do the same thing.
        Returns
        -------

        """
        # Proposed namespace manager context management functionality.
        # with NamespaceManager(self.name) as nsForThread:
        #     while not self.terminate:
        #         self.read()
        #         time.sleep(self.freq)
        if not cu.isReader(self.source):
            logging.error(f'Read Pipe {self.getName()} cannot run main read loop as source {self.source} is not a Reader.')
        if not cu.isDestination(self.destination):
            logging.error(f'Read Pipe {self.getName()} cannot run main read loop as destination {self.destination} is not a Destination.')
        while not self.isTimeToStop():
            self.read()
            time.sleep(self.freq)

    def run(self):
        """ Start the thread which will enact the read() method continuously. Also starts the Destination run loop
        (taking packages off of the input queue and calling handlePackage on them when required).

        :return:
        """
        self.readThread.start()
        ThreadedDestination.run(self)

    def end(self):
        """ Ends threading functionality of the read pipe.

        Setting terminate to True here will stop the main run() loop and exit that thread. Additionally, Destination.end()
        does the same thing (sets terminate to True) so the terminate is redundant (but good practise for clarity).

        :return:
        """
        ThreadedDestination.end(self)
        self.terminate = True
