from enum import Enum, auto

class ChannelType(Enum):
    """Enum used to specify which channel a specific stream/package/data belongs to.

    .. _channel-types:

    """
    Data = auto()
    Metadata = auto()
    Config = auto()
    Manifest = auto()
    DirConfig = auto()
    Command = auto()
    Response = auto()
    Event = auto()
    Index = auto()
    Log = auto()
    Other = auto()
    Base = auto()
    ProxyCommand = auto()
    ProxyResponse = auto()
    GUIInfo = auto()