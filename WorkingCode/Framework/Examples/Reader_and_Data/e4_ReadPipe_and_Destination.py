import time

from Framework.BaseClasses.Destination import Destination
from Framework.BaseClasses.Package import Package
from Framework.Examples.Reader_and_Data.e1_SimpleRead import SimpleReader
from Framework.Pipes.ReadPipe import ReadPipe

"""
    Example Four: Read Pipe and Destination
    
    A 'Read Pipe' is an object that 'sits' on top of a reader, and calls read periodically. It will wrap the results of 
    that read in a package, and send that package to its specified destination. It will do this with the healp of a thread
    that operates its own loop to read from a reader until instructed to end that loop. 
    
    This Read Pipe has a few important methods and properties that are essential to its functionality.
        - setSource(source)
            * Targets the supplied source as the target for the 'read' method. The source object MUST be a Reader of 
            some sort, as the readpipe will call 'source.read()'. 
        - setDestination(destination)
            * The outgoing package will be sent to the destination.accept(package) method. Therefore the supplied 
            destination object MUST be a Destination.  
        - start()
            * Begins threading functionality. Starts the runReading() method as well as the Destination.run() method.
        - runReading()
            * Calls the read() method of the read pipe until terminate is set to True. 
        - read()
            * Wraps the source.read() method. Puts the output of the source.read() method into a package and sends that to 
            the destination through its accept() method. 
        - end()
            * stops the Destination main loop as well as the runReading() method by setting terminate to True. 
        - handlePackage()
            * Since ReadPipe is a destination, it must be able to handle incoming packages. It does this by forwarding them
            to the destination, much like what the read() method does. 
    
    
    A Destination is a base class that can 'accept' a Package from another object in the Framework. 
    It is intended to operate in a threaded manner, where it will loop through a queue of incoming packages and handle 
    them; the handling implementation is left up to the sub class to implement. 
    
    The Destination class has a few important methods, some of which a subclass needs to implement
        Base Methods:
            - accept(package)
                * any package put onto the accept method will be handled by 'handlePackage'
            - start()
                * Begins threaded functionality. The 'accept' method will put incoming packages onto a queue to be handled, 
                which the main run() loop will then call 'handlePackage' on.
                Note: If accept is called before start is called, the package will go straight to the handlePackage method, skipping any queue.
                This could be dangerous if the destination is not set up for multi threaded applications
            - run()
                * take packages off of the queue and call handlePackage() on them.
        
        Subclass Implementation:
            - handlePackage 
                * A destination will need to implement and define handlePackage to decide what to do with incoming packages.
            
    Note:
        A ReadPipe is a destination, so it has two underlying threads. Therefore its start and end methods will handle its
        own thread as well as call the start and end method of its base class to ensure those resources are handled and
        cleaned up properly.  
"""

class DestinationPrint(Destination):
    def __init__(self, name):
        Destination.__init__(self, name)

    def handlePackage(self, package):
        """A necessary implementation of the Destination Base Class 'handlePackage'. """
        source = package.source
        pld = package.payload
        print(f'Destination {self.name} received a package from source {source} with the following payload:\n\t{pld}\n')

def main():
    r1name = 'Reader1'
    d1name = 'Destination1'

    # instantiate a reader. This is the SimpleReader found in example 1.
    reader1 = SimpleReader(r1name)

    # instantiate a destination object. This will simply print the contents of any package it receives.
    d1 = DestinationPrint(d1name)

    print('Reading and sending package to destination\n')
    pld1 = reader1.read()
    pkg1 = Package(source=r1name, payload=pld1)
    d1.accept(pkg1)
    print('\n\n')

    print('Setting up and starting ReadPipe. Frequency is once per second.\n')

    rp = ReadPipe('ReadPipe', source=reader1, destination=d1, freq=1)
    rp.start()
    time.sleep(4)
    rp.end()

    print('Ended ReadPipe reading.')



if __name__ == '__main__':
    main()