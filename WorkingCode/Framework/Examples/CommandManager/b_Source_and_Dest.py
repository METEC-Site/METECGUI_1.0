import sys
import time
from queue import Queue
from threading import Thread

from Framework.BaseClasses import Commands
from Framework.BaseClasses.Channels import ChannelType

module = sys.modules[__name__]
module.COMMANDID = 0

def main():
    pass

class CP(Thread, Commands.CommandClass):
    def __init__(self, name="CommandProcessor"):
        Thread.__init__(self)
        Commands.CommandClass.__init__(self, name)
        self.name = name
        self.inputQ = Queue()
        self.outputQ = Queue()

    # def getCPMetadata(self):
    #     if '_visibleCommands' in self.__dict__:
    #         return self._visibleCommands
    #     else:
    #         return []

    @Commands.CommandMethod
    def print(self, text):
        print(text)
        return text

    def emit(self, package):
        if self.CommandManager:
            self.CommandManager.accept(package)
        else:
            self.outputQ.put(package)

    def execute(self, package):
        # if package.channelType == ChannelType.Command:
        #     commandPL = package.payload
        #     command = commandPL.command
        #     args = commandPL.args
        #     kwargs = commandPL.kwargs
        #     if command in self._visibleCommands:
        #         method = self.__getattribute__(command)
        #         result = method(*args, **kwargs)
        #     else:
        #         result = "Could not execute {}, it does not exist within {}".format(command, self.name)
        #     if commandPL.commandLevel == Commands.CommandLevels.Immediate:
        #         return result
        # else:
        #     result = "Payload not executable: is not a command"
        # package.payload = package
        # package.channelType = ChannelType.CommandResponse
        # self.emit(package)
        pass

    def issueCommand(self, package):
        payload = package.payload
        command = payload['command']
        args = payload['args']
        func = getattr(self, command)
        ret = func(*args)
        payload['response'] = ret
        package.channelType = ChannelType.CommandResponse
        self.CommandManager.accept(package)

    def accept(self, package):
        self.inputQ.put(package)

    def run(self):
        while True:
            package = self.inputQ.get()
            # command = package.payload
            # if command.command in self._visibleCommands:
            #     method = self.__getattribute__(command.command)
            #     args = command.args
            #     kwargs = command.kwargs
            #     method(*args, **kwargs)
            # response = self.outputQ.get()
            # self.emit(response)
            pass


class CommandSource(Thread, Commands.CommandGenerator):
    def __init__(self, name="CommandGenerator"):
        Thread.__init__(self)
        Commands.CommandGenerator.__init__(self, name)
        self.name = name
        self.outputQ = Queue()

    def emit(self, package):
        if self.CommandManager:
            self.CommandManager.accept(package)
        else:
            self.outputQ.put(package)

    def receiveResponse(self, package):
        pass

    def run(self):
        while True:
            if not self.outputQ.empty() and self.CommandManager:
                while not self.outputQ.empty():
                    self.CommandManager.accept(self.outputQ.get())
            dest = 'CommandProcessor'
            func = 'print'
            args = ['Hello World']
            kwargs = {}
            package = self.CommandManager.createCommandPackage(self.name, "run", dest, func, args, kwargs)
            self.emit(package)
            time.sleep(1)





if __name__ == "__main__":
    main()