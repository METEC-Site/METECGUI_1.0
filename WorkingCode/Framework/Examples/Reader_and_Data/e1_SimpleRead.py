from Framework.BaseClasses.Readers.Reader import Reader
from Utils import TimeUtils as tu

'''
    Example One: Simple reader instantiation. 

    Readers can and should inherit from the Reader Base Class. If they do, they must implement the following attributes and methods
    * name - a unique name that should be used by this and only this instance of the class. No other obejcts in the framework instance
        should share this name. 
    * getName() - returns the name as specified by above.
    * metadata - Fields description and types corresponding 1:1 with  the fields provided by the read method. 
    * getReaderMetadata() gets the metadata associated with the reader.   
    * read() - returns a flat dictionary of values with keys matching the metadata provided and the types returned 
        matching the values of the returned metadata
    
    Notes:
        In general, the directory archiver expects there to be a 'timestamp' field with the type 'datetime - UTC epoch' 
        This is done to make accessing data easier when reading the csv files where timestamped data is stored. 
        
        The metadata values provided in the getReaderMetadata must be keys in the METADATA_TYPE_MAP, located in the 
        Framework.BaseClasses.Metadata directory.  
'''

class SimpleReader(Reader):
    def __init__(self, name):
        Reader.__init__(self, name)
        self.metadata = {
            'timestamp': 'datetime - UTC epoch',
            'field1': int,
            'field2': float,
            'field3': str
                        }

    def getName(self):
        return self.name

    def getReaderMetadata(self, sourceName=None):
        return self.metadata

    def read(self):
        return {
            'timestamp': tu.nowEpoch(),
            'field1': 1,
            'field2': 2.0,
            'field3': 'three'
                }

def main():

    ###
    # Readers must have the following methods defined:
        # getName
    r1 = SimpleReader('readerName')
    reading1 = r1.read()
    metadata1 = r1.getReaderMetadata()
    print(f'Result of reading from reader {r1.name}:                {reading1}')
    print(f'Result of getting metadata from reader {r1.name}:       {metadata1}\n')
    print(f'Keys of the dictionary returned by read must match the keys of the metadata returned by getReaderMetadata\n\n'
          f'Reading Keys :   {reading1.keys()}\n'
          f'Metadata Keys:   {metadata1.keys()}\n'
          f'Keys Match:      {reading1.keys() == metadata1.keys()}\n\n\n')

if __name__ == '__main__':
    main()