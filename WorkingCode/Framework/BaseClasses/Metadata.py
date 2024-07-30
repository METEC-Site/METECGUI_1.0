import json
from collections.abc import MutableMapping

from Utils import ClassUtils as cu


# Metadata needs to preserve order of fields in addition to type
# list of {'field': xx, 'type': Types.val} ??

# TODO: Move the typing from directory archiver here to a more accessible place.

class LoadError(Exception):
    pass

METADATA_TYPE_MAP = {
    int: int,
    float: float,
    str: str,
    bool: bool,
    'int': int,
    'float': float,
    'string': str,
    'double': float,
    'FLOAT32': float,
    'UINT8': int,
    'UINT16': int,
    "UINT32": int,
    "datetime - UTC epoch": float,
    "<class 'str'>": str,
    "<class 'int'>": int,
    "<class 'float'>": float
}

class Metadata(MutableMapping):
    __bases__ = [object, MutableMapping]

    # Inheriting from the Payload Base Class is necessary for any payload to be considered a 'payload' by the class utils
    def __init__(self, **kwargs):
        """each kwarg should either be a single value, the 'type' of the kwarg expected, or a dictionary with a 'type' field (among other metadata)
        """
        MutableMapping.__init__(self)
        self.map = {}
        for fieldname, fieldMetadata in kwargs.items():
            fieldMetadata = self.normalize(fieldMetadata)
            if not 'fieldname' in fieldMetadata.keys():
                fieldMetadata['fieldname'] = fieldname
            self.map[fieldname] = fieldMetadata
            # done so that you can access the value as an attribute.
            self.__dict__[fieldname] = fieldMetadata

    def __delitem__(self, key):
        if key in self.map.keys():
            del self.map[key]

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
        self.map[key] = value

    def __iter__(self):
        return iter(self.map)

    def __len__(self):
        return len(self.map)

    def __str__(self):
        return str(self.map)

    def keys(self):
        return self.map.keys()

    def values(self):
        return self.map.values()

    def items(self):
        return self.map.items()

    def normalize(self, md):
        if type(md) is dict:
            # this is the expected format, and must have 'type' as one of the fields.
            if not 'type' in md.keys():
                raise ValueError("Metadata must have a field named \'type\' as one of the fields.")
        else:
            md = {'type': md}
        # elif type(md) is type:
        #     # this is the type for the specified field.
        #     md = {'type': md}
        # elif md in METADATA_TYPE_MAP.keys():
        #     md = {'type': md}

        self.checkType(md['type'])
        return md


    def checkType(self, t):
        if not type(t) is type and not t in METADATA_TYPE_MAP.keys():
            raise TypeError(f"type ({t}) of the field myst be of 'type' or must appear in METADATA_TYPE_MAP keys.")

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

def mdFromJson(jsonConfig, archiver=None):
    loadedJson = None
    md = None
    parsedMetadata = None
    if type(jsonConfig) is dict:
        # if the json is loaded in as dict, use that to load the metadata.
        try:
            parsedMetadata = Metadata(**jsonConfig)
        except:
            parsedMetadata = jsonConfig
    if cu.isArchiver(archiver):
        try:
            # try to load from config read by archiver
            loadedJson = json.loads(archiver.readConfig(jsonConfig))
            if loadedJson:
                try:
                    parsedMetadata = Metadata(**loadedJson)
                except:
                    if type(loadedJson) is dict:
                        parsedMetadata = loadedJson
        except:
            pass
    if not loadedJson and type(jsonConfig) is str:
        # if not loaded config from archiver, try to open as filepath
        try:
            with open(jsonConfig) as lf:
                loadedJson = json.load(lf)
                try:
                    parsedMetadata = Metadata(**loadedJson)
                except:
                    if type(md) is dict:
                        parsedMetadata = loadedJson
        except:
            parsedMetadata = None

    if parsedMetadata is None:
        raise LoadError(f'Could not load metadata from archiver or filepath.'
                        f'\n\timproper config: {jsonConfig}')
    return parsedMetadata