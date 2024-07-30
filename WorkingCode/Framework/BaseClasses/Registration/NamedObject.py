class NamedObject():
    insts = 0
    def __init__(self, name=None, **kwargs):
        super().__init__(**kwargs)
        self.setInstanceName(name)

    def setInstanceName(self, name=None):
        if name is None:
            name = f"{self.__class__.__name__}_{NamedObject.insts}"
            NamedObject.insts += 1
        self.instanceName = name

    def getName(self):
        return self.instanceName