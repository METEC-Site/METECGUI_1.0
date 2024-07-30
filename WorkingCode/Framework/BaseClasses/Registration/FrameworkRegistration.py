from Framework.BaseClasses.NamedObject import NamedObject
from Framework.BaseClasses.Registration.ObjectRegister import Registry

class FrameworkObject(NamedObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Registry.registerObject(self, self.getName())