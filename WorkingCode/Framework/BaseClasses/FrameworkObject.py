from abc import ABC, abstractmethod, ABCMeta
import logging

from Framework.Manager.ObjectManager import ObjectManager
import logging
from abc import ABC, abstractmethod, ABCMeta

from Framework.Manager.ObjectManager import ObjectManager


class FOMetaclass(ABCMeta, type):
    pass

# old definition of FOMetaclass
# moved the __new__ and _instanceMapping into the base class as this was causing issues on import (metaclass __new__ is called on import)
# https://www.python.org/dev/peps/pep-3115/ see Invoking the Metaclass
# class FOMetaclass(ABCMeta, type):
#     pass
#     _instanceMapping = {}
#
#     def __new__(cls, *args, **kwargs):
#         name = None
#         if args:
#             name = args[0] # todo: make uniform that args[0] is name if args are passed at all
#         if (name is None) or not (type(name) is str):
#             name = kwargs['name']
#
#         # if not name in cls._instanceMapping.keys():
#         #     inst = super(FOMetaclass, cls).__new__(cls, *args, **kwargs)
#         #     cls._instanceMapping[name] = inst
#         # changed to debug the issue with inability to operate the GUI/main window PyQt conflicts.
#         if name in cls._instanceMapping.keys():
#             logging.warning(f'Object with name {name} already exists in Framework; will overwrite original object with new instantiation.')
#         inst = super(FOMetaclass, cls).__new__(cls, *args, **kwargs)
#         cls._instanceMapping[name] = inst
#         return cls._instanceMapping[name]

class FrameworkObject(ABC, metaclass=FOMetaclass):
    stopper = None
    # _instanceMapping = {}

    # this caused some issues to is removed to make more stable.
    # def __new__(cls, *args, **kwargs):
    #     name = None
    #     if args:
    #         name = args[0] # todo: make uniform that args[0] is name if args are passed at all
    #     if (name is None) or not (type(name) is str):
    #         name = kwargs['name']
    #
    #     if not name in cls._instanceMapping.keys():
    #         inst = super().__new__(cls, *args, **kwargs)
    #         cls._instanceMapping[name] = inst
    #     return cls._instanceMapping[name]


    def __init__(self, name=None, namespace=None):
        # self.stopper = threading.Event()
        self.stopper = ObjectManager.getStopper()
        self.name = name
        if namespace is None:
            self.namespace = ObjectManager.getProcessNamespace()
        else:
            self.namespace = namespace
        if self.name:
            ObjectManager.registerObject(self, self.name, self.namespace)
        self.logger = logging.getLogger(self.name)

    def resetLogger(self):
        self.logger = logging.getLogger(self.name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._onExitCleanup()

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def end(self):
        try:
            self.stopper.set()
        except Exception as e:
            self.logger.exception(f'Could not end base class functionality for Framework Object {self.name} due to exception {e}')

    @abstractmethod
    def _onExitCleanup(self):
        self.logger.debug(f'_onExitCleanup called from Base Class FrameworkObject named {self.name}')
        ObjectManager.unregisterObject(self)

    # @abstractmethod
    def handleHeartbeat(self):
        # self.logger.info(f'Heartbeat from {self.name}')
        # print(f'Heartbeat from {self.name}')
        pass

    def isTimeToStop(self):
        if not (self.stopper is None):
            try:
                if self.stopper.is_set():
                    return True
                return False
            except Exception as e:
                self.logger.exception(f'Could not access stopper for thread {self.name}')
        return True

    def getName(self):
        return self.name

    def setNamespace(self, namespace):
        self.namespace = namespace

    def getNamespace(self):
        return self.namespace