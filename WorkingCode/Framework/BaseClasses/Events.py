import logging
from enum import Enum, auto

from Framework.BaseClasses.Package import Payload


class EventTypes(Enum):
    Default = auto()
    Timeout = auto()
    ConnectTimeout = auto()
    Connected = auto()
    Disconnected = auto()
    GUIEvent = auto()
    Annotation = auto()
    Shutdown = auto()
    FileUpdate = auto()
    LockWidget = auto()
    CalStart = auto()
    CalEnd = auto()
    MainStart = auto()
    MainEnd = auto()
    Emission = auto()
    ExperimentStart = auto()
    ExperimentEnd = auto()
    ExperimentEdit = auto()

class EventPayload(Payload):
    __bases__ = [Payload]
    def __init__(self, source=None, eventType=EventTypes.Default, timestamp=None, msg="", namespace=None, **kwargs):
        if not eventType in EventTypes:
            logging.info(f"EventPayload given incorrect EventType: {eventType}. Changed to Default")
            eventType = EventTypes.Default
        Payload.__init__(self, source, timestamp, namespace=namespace, msg=msg, eventType=eventType, **kwargs)

    # def toDict(self):
    #     d = dict(timestamp=self.timestamp, source=self.source, eventType=self.eventType, msg=self.msg)
    #     return d