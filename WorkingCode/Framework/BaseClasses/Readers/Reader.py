from abc import ABC, abstractmethod

# from Framework.BaseClasses.FrameworkObject import FOMetaclass, FrameworkObject # commented out to transition to Frameworkv2
from Framework.BaseClasses.Registration.FrameworkRegistration import FrameworkObject


class Reader(FrameworkObject, ABC):
    def __init__(self, name, **kwargs):
        super().__init__(name=name, **kwargs)

    @abstractmethod
    def getReaderMetadata(self, sourceName=None):
        """A method to get metadata of the fields returned by a 'read'

                The cfg object returned by this method must be either a flat dictionary or a Metadata object (from Metadata base class)
                The keys MUST be the same as the keys of the dictionary returned by a 'read' for the data to be archived correctly.

                If using a flat dictionary:
                    values should be the type of that field when read. See Metadata.METADATA_TYPE_MAP for all current types.
                    ex:
                    {
                     'timestamp': float, (note that timestamp should be Epoch time always)
                     'value1': int,
                     ...}
                If using Metadata Base Class:
                    The Metadata base class is addressable like a mutable mapping: IE a dictionary.
                    values should be a dictionary, with bare minimum "type" as one of the key/value pairs.
                    ex: (represented as a dictionary)
                    {'
                    timestamp':{'type': float, 'notes': 'Epoch Time of read', 'units': 'Epoch'},
                    'value1': {'type':int, 'notes': 'the first value of the read': 'foo':'bar'},
                    ...}
                """
        raise NotImplementedError

    @abstractmethod
    def read(self):
        raise NotImplementedError