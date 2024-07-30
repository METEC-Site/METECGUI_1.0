import datetime
from collections.abc import MutableMapping
from threading import RLock

from Framework.BaseClasses.Channels import ChannelType
from Utils import ClassUtils as cu
from Utils import TimeUtils as tu


class Package:
    packageID = 0
    lock = RLock()
    """ A class intended to instill uniformity throughout the framework for how the deliverable dictionary is accessed.

    self.source: a string containing the name of the object from which the payload was collected.
    self.timestamp: an epoch time representation of the time at which the payload was collected or the time at which the
        payload object was instantiated if no timestamp was provided.
    self.payload: the deliverable 
    """
    def __init__(self, source=None, timestamp=None, payload=None, metadata=None, channelType=ChannelType.Other, mdKey=None, **kwargs):
        self.channelType = channelType
        self.timestamp = timestamp if timestamp else tu.nowEpoch()
        self.source = source
        self.metadata = metadata
        self.metadataKey = mdKey
        with Package.lock:
            self.packageID = Package.packageID
            Package.packageID += 1
        self.payload = payload

    def toDict(self):
        plType = type(self.payload)
        if plType is dict:
            # already good to go!
            dictPL = self.payload
        elif cu.isPayload(self.payload):
            dictPL = self.payload.toDict()
        else:
            # What to do if it isn't a payload or dict?
            dictPL = self.payload

        retPkg = {
            'source': self.source,
            'timestamp': self.timestamp,
            'channelType': self.channelType,
            'packageID': self.packageID,
            'payload': dictPL
        }
        return retPkg

# class Payload(ABC, MutableMapping):
class Payload(MutableMapping):
    # __bases__ = [object, MutableMapping]

    # Inheriting from the Payload Base Class is necessary for any payload to be considered a 'payload' by the class utils
    def __init__(self, source, timestamp=None, metadata=None, **kwargs):
        if timestamp is None:
            # default to now epoch.
            timestamp = tu.nowEpoch()
        if type(timestamp) is datetime.datetime:
            # Expecting timestamp in epoch (float)
            timestamp = tu.DTtoEpoch(timestamp)
        if timestamp is None:
            timestamp = tu.nowEpoch()
        self.map = {}
        self.source = source
        self.metadata = metadata
        self.timestamp = timestamp
        self.map['source'] = source
        self.map['timestamp'] = timestamp
        for kw, value in kwargs.items():
            self.map[kw] = value
            # done so that you can access the value as an attribute.
            self.__dict__[kw] = value

    def __delitem__(self, key):
        if key in self.map.keys():
            del self.map[key]
        if key =='source':
            del self.source
        if key == 'timestamp':
            del self.timestamp

    def __getattr__(self, item):
        try:
            return MutableMapping.__getattribute__(self, item)
        except AttributeError as e:
            return None

    def __getitem__(self, item):
        return self.map[item]

    def __setitem__(self, key, value):
        if key in self.map.keys():
            del self[key]
        if key == 'source':
            self.source = value
        if key == 'timestamp':
            self.timestamp = value
        self.map[key] = value

    def __iter__(self):
        return iter(self.map)

    def __len__(self):
        return len(self.map)

    def __str__(self):
        # doing this breaks internal map structure. Do another way. Shouldn't be a problem in PY 3.6+ because all dicts
        # are ordered here.
        # ts = self.map.pop('timestamp')
        # source = self.map.pop('source')
        # # TODO: better default dtToStr?
        # readableTS = tu.dtToStrNormalTZ(tu.EpochtoDT(self.timestamp))
        # self.map = {'timestamp':readableTS, 'source': source, **self.map}
        return str(self.map)

    # def __dict__(self):
    # Overwriting __dict__ this way will hide all other attributes not in self.map, which could lead to problems.
    # Better to leave it undone.
    #     print("dict")
    #     return dict(self.map)

    def __repr__(self):
        return f"{type(self).__name__}({self.map})"

    # abstract method because this used to be a base class. Now it has an implementation, not sure if just ABC is the
    # way to go.
    # @abstractmethod
    def toDict(self):
        return self.map

def main():
    pl = Payload('One', 123.45)
    pl['dest'] = 'There'
    print(pl)

if __name__ == '__main__':
    main()