import tempfile
import time

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses.Channels import ChannelType
from Framework.Examples.Reader_and_Data.e4_ReadPipe_and_Destination import DestinationPrint
from Framework.Examples.Reader_and_Data.e5_IntervalReader_and_Threading import ExampleIntervalReader
from Framework.Manager.DataManager import DataManager

"""
    Example Five: Interval Reader with Data Manager

    In this example, data read by a reader is sent to the data manager, which archives and publishes that data package to 
    all units that are subscribed to that data.  

"""

def main():
    with tempfile.TemporaryDirectory() as tdir:
        print('Starting example 6a')
        #Instantiate an archiver that will save the incoming data/packages.
        da1 = DirectoryArchiver(baseDir=tdir)

        # Create the DataManager that will forward packages to the archiver.
        dm = DataManager(archiver=da1, name='DataManager')

        # Create a reader instance.
        r1name = 'reader1'
        reader1 = ExampleIntervalReader(name=r1name, destination=dm, readInterval=.5)

        da1.createChannel(reader1.getName(), channelType=ChannelType.Data, metadata=reader1.getReaderMetadata())
        # start reading for about 5 seconds, then stop.
        print(f'Start reading from {reader1.getName()}')
        reader1.start()
        time.sleep(2)
        reader1.end()
        print(f'Ending reading from {reader1.getName()}')


        print('Obtaining archived readings from Archiver')
        readings = da1.read(channel=r1name)
        for line in readings:
            print(line)

        da1.end()
        dm.end()

    with tempfile.TemporaryDirectory() as tdir:
        print('\n\nStarting example 6b')

        # make the archiver, destination, reader, and manager.
        da2 = DirectoryArchiver(baseDir=tdir)
        d2 = DestinationPrint('Destination2')
        dm2 = DataManager(archiver=da2)
        r2 = ExampleIntervalReader('Reader2', destination=dm2, readInterval=.5)
        r3 = ExampleIntervalReader('Reader3', destination=dm2, readInterval=.5)

        # The destination d2 must subscribe to the DataManager. If publisherName is not specified, d2 will get ALL data
        # from ALL subscribers. if publisherName is specified, only packages with sources matching the name of publisherName
        # will be sent to the destination


        # dm2.subscribe(d2)
        # only packages from r2 will be sent to d2.
        dm2.subscribe(d2, publisherName=r2.getName())

        # start the archiver, followed by the data manager and then reader. These now operate in their own threads.
        print('Starting readers and sending packages to DataManager.')
        # da2.start()
        # dm2.start()
        # d2.start()
        r2.start()
        r3.start()

        time.sleep(2)
        r2.end()
        r3.end()
        i=-10



if __name__ == '__main__':
    main()