from abc import ABC, abstractmethod

# from Framework.BaseClasses.FrameworkObject import FOMetaclass, FrameworkObject # commented out to transition to Frameworkv2
from Framework.BaseClasses.Registration.FrameworkRegistration import FrameworkObject


class Writer(FrameworkObject, ABC):
    def __init__(self, name):
        FrameworkObject.__init__(self, name=name)

    @abstractmethod
    def write(self, obj):
        pass