import tempfile
import time

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Metadata import Metadata
from Framework.BaseClasses.Package import Package
from Framework.BaseClasses.Readers.Reader import Reader
from Framework.Examples.Reader_and_Data.e1_SimpleRead import SimpleReader
from Utils import TimeUtils as tu

"""
    Example Three: Archived Read, alternate metadata 

    This example is functionally the same as e2_ArchivedRead, except that the metadata in this case is not a dictionary 
    but rather a custom class that stores more information. In essence it is a mutable mapping (a dictionary) that has 
    added methods that help it work with other parts of the framework. 
    
    The Metadata class expects takes dictionaries as keyword arguments. These dictionaries should have 'type':[TYPE] as a 
    key/value, and then any number of extra descriptors expanding on that.
    'field1' :{
        'type': [TYPE],
        '[descriptor1]' : [DESCRIPTOR_VALUE_1]
    }
    
    The Metadata class will be a mapping of these fields, accessable like a normal dictionary. 
    IE to access the type of field 1 can be accessed through Metadata['field1']['type']. 
    
    Some features of this custom metadata include:
        - Writing multiple lines of header on a csv. The 'type' field must be present and follow the same rules as the regular metadata 
            ( IE the type must appear in the METEDATA_TYPE_MAP) 
        - In addition to the user provided metadata for each field, the field's name (key) will be stored in that dictionary under 
            'fieldname'
    
"""

#################################
##### CUSTOM METADATA CLASS #####
#################################

classMetadataFields = {
    'timestamp': {
        'type': 'datetime - UTC epoch',
        'units': 'seconds',
        'notes': 'This is a note for the time.'
    },
    'field1':{
        'type': int,
        'units': 'f1'
    },
    'field2':{
        'type': float,
        'units': 'f2'
    },
    'field3':{
        'type': str,
        'units': 'f3'
    }
}

classMetadata = Metadata(**classMetadataFields)

# two ways of accessing information from the Metadata Class Instance.
tsMetadata = classMetadata['timestamp']
alternateTSMetadata = classMetadata.timestamp

#############################################
##### Reader Definition - uses Metadata #####
#############################################

class ReaderCustomMD(Reader):
    def __init__(self, name):
        Reader.__init__(self, name)
        self.metadata = classMetadata

    def getReaderMetadata(self, sourceName=None):
        return self.metadata

    def read(self):
        time.sleep(.1)
        return {
            'timestamp': tu.nowEpoch(),
            'field1': 1,
            'field2': 2.0,
            'field3': 'three'
        }

    def getName(self):
        return self.name

###########################
##### Main event loop #####
###########################


def main():
    # unwrap these fields in the metadata class. Now these fields and the metadata for them can be accessed like a dictionary.
    print(f'Metadata for timestamp:\n\t{tsMetadata}\n')
    print(f'Alternate way of accessing timestamp:\n\t{alternateTSMetadata}\n')

    with tempfile.TemporaryDirectory() as tdir:
        da = DirectoryArchiver(baseDir=tdir)

        # Reader_and_Data instantiation.
        simpleReader = SimpleReader('simpleReader')
        mdReader = ReaderCustomMD('metadataReader')

        # Before data can be stored in the archiver, a channel must be created. The name of the channel should generally
        #  be the name of the reader.
        # The metadata supplied can be either a dictionary or a Metadata class.
        # The key thing is that the fields supplied in the metadata match 1:1 with data supplied by a read.
        da.createChannel(name=simpleReader.getName(), channelType=ChannelType.Data,
                         metadata=simpleReader.getReaderMetadata())
        da.createChannel(name=mdReader.getName(), channelType=ChannelType.Data, metadata=mdReader.getReaderMetadata())

        # Make a reading, and put that read in a package. The 'source' as defined by the package must match with the
        # channel name created above in order to be stored in the archive.
        simplePayload = simpleReader.read()
        simplePackage = Package(source=simpleReader.getName(), payload=simplePayload, channelType=ChannelType.Data)

        # Make another reading
        mdPayload = mdReader.read()
        mdPackage = Package(source=mdReader.getName(), payload=mdPayload, channelType=ChannelType.Data)

        # To save the reading in the archive, send the package with the data to the archiver's accept method.
        da.accept(simplePackage)
        da.accept(mdPackage)

        print(f'Data stored in archiver for {simpleReader.getName()}: \n\n {da.read(simpleReader.getName())}\n')
        print(f'Data stored in archiver for {mdReader.getName()}: \n\n {da.read(mdReader.getName())}\n')

if __name__ == '__main__':
    main()