import logging
import os
from threading import Thread

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses import Commands
from Framework.BaseClasses.Channels import ChannelType
from Framework.Manager import CommandManager
from Framework.Pipes.ThreadedPipe import ThreadedPipe

BASE_DIR = os.path.join(__file__, "./../../../../CommandFramework")
archiveTemplate = "./Examples/CommandManager/test/%Y%m%d"

# TODO: Make it so that the command generators and processors don't do any direct package management.

def main():
    threads = []
    with DirectoryArchiver("Directory Archiver", BASE_DIR, archiveTemplate) as da:
        ARCHIVE_BUS = ThreadedPipe(destinations=da)
        threads.append(ARCHIVE_BUS)
        cm = CommandManager.CommandManager(name='CommandManager')
        cm.registerArchiver(da)
        threads.append(cm)
        cc = CommandCascader(commandManager=cm)
        cm.registerCommandClass(cc)
        threads.append(cc)
        da.createChannel(cm.name, ChannelType.Command)
        for thread in threads:
            thread.start()
        cc.startChain()
    pass


class CommandCascader(Commands.CommandClass, Thread):
    def __init__(self, name="CommandCascader", commandManager=None):
        Thread.__init__(self)
        self.name = name
        Commands.CommandClass.__init__(self, name)
        self.CommandManager = commandManager

    def emit(self, package):
        if self.CommandManager:
            return self.CommandManager.accept(package)
        else:
            logging.debug("No Command TestSuite set for {}".format(self.name))

    def handleResponse(self, package):
        i=-10
        pass

    def startChain(self):
        command = "COMMAND_ONE"
        package = self.CommandManager.createCommandPackage(self.name, 'startChain', self.name, command, [], {})
        return self.emit(package)

    @Commands.CommandMethod
    def COMMAND_ONE(self, *args, **kwargs):
        command = "COMMAND_TWO"
        callerID = self.COMMAND_ONE.__dict__['_caller_ID']
        package = self.CommandManager.createCommandPackage(self.name, "COMMAND_ONE", self.name, command, [], {},
                                                           callerID=callerID)
        return self.emit(package)
        pass

    @Commands.CommandMethod
    def COMMAND_TWO(self, *args, **kwargs):
        command = "COMMAND_THREE"
        callerID = self.COMMAND_TWO.__dict__['_caller_ID']
        package = self.CommandManager.createCommandPackage(self.name, "COMMAND_TWO", self.name, command, [], {},
                                                           callerID=callerID)
        return self.emit(package)


    @Commands.CommandMethod
    def COMMAND_THREE(self, *args, **kwargs):
        return "This is Command Three"


if __name__ == "__main__":
    main()