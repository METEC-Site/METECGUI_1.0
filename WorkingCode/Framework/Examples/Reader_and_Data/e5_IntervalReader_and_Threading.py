import time

from Framework.BaseClasses.Readers.IntervalReader import IntervalReader
from Framework.Examples.Reader_and_Data.e3_AlternateMetadata import classMetadata
from Framework.Examples.Reader_and_Data.e4_ReadPipe_and_Destination import DestinationPrint
from Utils import TimeUtils as tu

"""
    Example Five: Interval Reader

    In this example, threading is used to achieve a read on a periodic interval. The IntervalReader inherits from Reader
    Base Class, and adds a few additional methods to help manage threading and piping the data to where it needs to go.
    Check out the class definition of IntervalReader for a more in depth look at what it adds, summarized below.
    
    Useful Methods:
        - start()
            * Starts the interval reading by setting up and starting a read pipe. (See example 4 for more information)            
        - end()
            * call end() on its ReadPipe as well as on the base class, Reader()
            * ReadPipe: stops threading and exits the main 'read' loop. Finishes last read and then no more reads will be sent.
            * Reader: calls _onExitCleanup of this class. 
        - _onExitCleanup()
            * called with the Reader.end() method through the Base Class. Since this class inherits from only one base 
            class, redefining _onExitCleanup is optional as it is already implemented in the base class.     
"""


class ExampleIntervalReader(IntervalReader):
    """This class is an example of how to subclass the IntervalReader base class."""

    def __init__(self, name, destination=None, readInterval=1):
        IntervalReader.__init__(self, name, destination=destination, readInterval=readInterval)

    # Threading starting/stopping and resource allocation/freeing methods.

    def start(self):
        """Method that invokes the parent class start method.

        The start method of interval reader will begin reading on an interval, and sending that to the supplied destination.
        """
        print('Starting interval reader read thread.')
        IntervalReader.start(self)

    def end(self):
        """ To incorporate threading effectively, it is necessary to call IntervalReader.end() to free up resources/end
        the loop of the IntervalReader's readPipe"""
        print('Ending interval reader read thread.')
        IntervalReader.end(self)

    def _onExitCleanup(self):
        """ A method intended to clean up any used resources, if any, after the end() of the instance. If inheriting from
        multiple base classes, call _onExitCleanup on both base class instances."""
        IntervalReader._onExitCleanup(self)

    # Data/attribute accessors

    def getName(self):
        return self.name

    def getReaderMetadata(self, sourceName=None):
        return classMetadata

    def read(self):
        return {
            'timestamp': tu.nowEpoch(),
            'field1': 1,
            'field2': 2.0,
            'field3': 'three'
        }


def main():
    irName = 'IntervalReader1'
    d1 = DestinationPrint('CustomDestination')

    # create the intervalReader object
    ir = ExampleIntervalReader(irName, destination=d1, readInterval=1)

    # set the destination of this instance (and the underlying readPipe)
    ir.start()

    time.sleep(5)
    ir.end()
    pass

if __name__ == '__main__':
    main()