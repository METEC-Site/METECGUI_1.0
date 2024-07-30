from Framework.BaseClasses import Commands
from Framework.BaseClasses.Destination import Destination
from Framework.BaseClasses.Worker import Worker

class TestManager(Worker, Destination, Commands.CommandClass):
    def __init__(self, name="TestManager",
                 archiver=None, commandManager=None, dataManager=None, eventManager=None,
                 blocking=True, qtimeout=None,
                 **kwargs):
        Worker.__init__(self, archiver, commandManager, dataManager, eventManager, name)
        Destination.__init__(self, name)
        Commands.CommandClass.__init__(self, name=name)
        self.name = name
        self.configs = None
        self.stopTest = False
        self.blocking = blocking
        self.qtimeout = qtimeout
        self.csMetadata = {'name': self.name}

    def getcsMetadata(self):
        return self.csMetadata

    def emit(self, package):
        self._emitCommand(package)

    def handleResponse(self, package):
        i=-10
        pass

    def handlePackage(self, package):
        pass

    def execute(self, package):
        pass

    @Commands.CommandMethod
    def CLOSEALLVALVES(self, *args, **kwargs):
        pads = args
        labjacks = list(filter(lambda x: x['labjack'] and x['pad'] in pads, self.configs['pads']))
        ljNames = [labjack['labjack'] for labjack in labjacks]

        returns = {}
        for name in ljNames:
            # TODO: How to map command string to method name???
            command = "closeAllValves"
            cmd = Commands.CommandPayload(commandLevel=Commands.CommandLevels.Immediate, )
            package = self.CommandManager.createCommandPackage(self.name, "CLOSEALLVALVES", name, command, args=[], kwargs={})
            returns[name] = self.emit(package)
        if not True in list(returns.values()):
            return False
        return True

    @Commands.CommandMethod
    def OPENVALVES(self, *args, **kwargs):
        valves = args
        sensorProperties = list(filter(lambda x: x['name'] in valves, self.configs['sensors']))
        for sensor in sensorProperties:
            valveName = sensor['name']
            labjack = sensor['labjack']
            command = 'openValve'
            package = self.CommandManager.createCommandPackage(self.name, "OPENVALVES", labjack, command, [valveName], {})
            self.emit(package)

    @Commands.CommandMethod
    def CLOSEVALVES(self, *args, **kwargs):
        valves = args
        sensorProperties = list(filter(lambda x: x['name'] in valves, self.configs['sensors']))
        for sensor in sensorProperties:
            valveName = sensor['name']
            labjack = sensor['labjack']
            command = 'closeValve'
            package = self.CommandManager.createCommandPackage(self.name, "CLOSEVALVES", labjack, command, [valveName], {})
            self.emit(package)