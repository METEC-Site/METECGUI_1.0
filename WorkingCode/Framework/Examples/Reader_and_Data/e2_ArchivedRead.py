import tempfile

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Package import Package
from Framework.Examples.Reader_and_Data.e1_SimpleRead import SimpleReader

'''
    Example Two: Archived Read 

    Data that is read generally should be archived somehow. In this example, the data is sent to the DirectoryArchiver,
    which handles incoming data and stores it in a csv with the name provided by the createChannel method. This csv is located
    in the directory provided to the archiver (in this case a temporary directory that is cleaned up after the method exits. 
    
    Before data can be stored, a few things must happen
        * The archiver must be instantiated and pointed to a directory to store the data (baseDir argument)
        * A reader should be instantiated with a read() method that provides data and metadata (see e1_SimpleRead)
        * A channel should be created in the archiver 
            - The channel type should be ChannelType.Data 
                (this tells the archiver to expect an incoming stream to be stored in the '/data/' subdirectory)
            - The metadata passed should be the same as the data provided by the read (though some caveats are allowed, see e3_AlternateMetadata)
        * The data should be read and put into a Package. The source should match the name provided in the createChannel method. 
        * That package needs to be passed to the archiver. This is done by calling the archiver's 'accept()' method with the package as the argument. 
            - In threaded mode (not seen in this example), this will put the package on the archiver's queue to be handled by its thread.
    
    Data can then be accessed by calling 'read' on the archiver, with the channelName argument being the source name of the channel 
    wanting to be read, and the channelType argument being ChannelType.Data.  
        
    Notes:
        In general, the directory archiver expects there to be a 'timestamp' field with the type 'datetime - UTC epoch' 
        This is done to make accessing data easier when reading the csv files where timestamped data is stored. 
        
        The location of the directory created is in the os system's temporary directory. On windows, enter %appdata% into
        the search bar, and brows to local AppData/Local/Temp. 
'''

def main():
    with tempfile.TemporaryDirectory() as tdir:

        #Instantiate an archiver that will save the incoming data/packages.
        da = DirectoryArchiver(baseDir=tdir)

        # IntervalReader instantiation.
        simpleReader = SimpleReader('simpleReader')

        # Before data can be stored in the archiver, a channel must be created. The name of the channel should generally
        #  be the name of the reader.
        # The metadata supplied can be either a dictionary or a Metadata class.
        # The key thing is that the fields supplied in the metadata match 1:1 with data supplied by a read.
        da.createChannel(name=simpleReader.getName(), channelType=ChannelType.Data,
                         metadata=simpleReader.getReaderMetadata())

        # Make a reading, and put that read in a package. The 'source' as defined by the package must match with the
        # channel name created above in order to be stored in the archive.
        simplePayload = simpleReader.read()
        simplePackage = Package(source=simpleReader.getName(), payload=simplePayload, channelType=ChannelType.Data)

        # To save the reading in the archive, send the package with the data to the archiver's accept method.
        da.accept(simplePackage)

        print(f'Data stored in archiver for {simpleReader.getName()}: \n\n {da.read(simpleReader.getName())}\n')


if __name__ == '__main__':
    main()
