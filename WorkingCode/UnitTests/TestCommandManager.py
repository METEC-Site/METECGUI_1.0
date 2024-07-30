import tempfile
import threading
import unittest

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Commands import CommandClass, CommandMethod
from Framework.Manager.CommandManager import CommandManager
from UnitTests import TestAll as TA
from Utils import ClassUtils as cu


class TestCommandClass(CommandClass):
    def __init__(self, name, CommandManager=None):
        CommandClass.__init__(self, name, CommandManager)
        self.responsesReceived = []
        self.commandsSent = []
        self.commandsReceived = []

    def accept(self, package):
        pass

    def start(self):
        pass

    def end(self):
        pass

    def handlePackage(self, package):
        pass

    @CommandMethod
    def sendTestCommand(self, destinationName=None):
        destinationName = destinationName if destinationName else self.name
        testPackage = self.createCommandPackage('sendTestCommand', destinationName, 'receiveTestCommand', [], {})
        result = self._emitCommand(testPackage)
        self.commandsSent.append(testPackage)
        return result

    @CommandMethod
    def receiveTestCommand(self):
        return True

class TestCommandManager(unittest.TestCase):

    @TA.CleanNamespace('test_Startup')
    def test_Startup(self):
        with tempfile.TemporaryDirectory() as tdir:
            with DirectoryArchiver(name='StartupArchiver', baseDir=tdir) as DA:
                cm = CommandManager(DA, 'startupCM')
                isCM = cu.isCommandManager(cm)
                self.assertEqual(isCM, True)


    @TA.CleanNamespace('test_Received')
    def test_Received(self):
        with tempfile.TemporaryDirectory() as tdir:
            with DirectoryArchiver(name='receivedArchiver', baseDir=tdir) as DA:
                cm = CommandManager(DA, 'receivedCM')
                tcc = TestCommandClass("TCC1", cm)
                cm.registerCommandClass(tcc)
                response = tcc.sendTestCommand()
                self.assertEqual(response, tcc.receiveTestCommand())

    @TA.CleanNamespace('test_Archiver')
    def test_Archiver(self):
        with tempfile.TemporaryDirectory() as tdir:
            with DirectoryArchiver(name='archiver', baseDir=tdir) as da:
                cm = CommandManager(da, 'archiverCM')
                cm.registerArchiver(da)
                tcc = TestCommandClass("TCCarchiver", cm)
                cm.registerCommandClass(tcc)
                result = tcc.sendTestCommand()
                self.assertEqual(result, tcc.receiveTestCommand())
                sentPackages = tcc.commandsSent
                receivedPackages = tcc.commandsReceived
                # archivedPackages = da.readCommands()
                archivedPackages = []
                for channelName, channelTypes in da.getChannels().items():
                    for channelType in channelTypes:
                        if channelType == ChannelType.Command:
                            reading = da.read(channelName, channelType)[0]
                            archivedPackages = [*archivedPackages, *reading]
                for sent in sentPackages:
                    pl = sent.payload
                    self.assertEqual(pl.toDict() in archivedPackages, True)
                for received in receivedPackages:
                    pl = received.payload
                    self.assertEqual(pl.toDict() in archivedPackages, True)

    @TA.CleanNamespace('test_getCommandID')
    def test_getCommandID(self):
        with tempfile.TemporaryDirectory() as tdir:
            with DirectoryArchiver(name='idArchiver', baseDir=tdir) as DA:
                cm = CommandManager(DA, 'idCM')
                ret1 = []
                ret2 = []
                threads = []
                for i in range(20):
                    threads.append(threading.Thread(target=commandIDThread, args=(cm, ret1)))
                    threads.append(threading.Thread(target=commandIDThread, args=(cm, ret2)))

                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
                retSet = [value for value in ret1 if value in set(ret2)]
                self.assertEqual(len(retSet) == 0, True)

    @TA.CleanNamespace('test_commandPackageLoop')
    def test_commandPackageLoop(self):
        with tempfile.TemporaryDirectory() as tdir:
            with DirectoryArchiver(name='pkgLoopArchiver', baseDir=tdir) as DA:
                cm = CommandManager(DA)
                tcc = TestCommandClass("TCCloop", cm)
                cm.registerCommandClass(tcc)
                cm.registerCommandClass(tcc)
                for i in range(200):
                    tcc.sendTestCommand("TCCloop")
                crs = []
                for command in tcc.commandsSent:
                    for response in tcc.responsesReceived:
                        if command.payload.commandID == response.payload.commandID:
                            crs.append((command, response))
                crDict = dict(map(lambda x: (x[0].payload.commandID, {'commandPackage': x[0], 'responsePackage':x[1]}), crs))
                for cID, cr in crDict.items():
                    self.assertEqual(cr['commandPackage'] in list(cm.cachedTransactions.get(cID, {}).values()), True)
                    self.assertEqual(cr['responsePackage'] in list(cm.cachedTransactions.get(cID, {}).values()), True)
                    self.assertEqual(cr['commandPackage'] in list(cm.transactions.get(cID, {}).values()), False)
                    self.assertEqual(cr['responsePackage'] in list(cm.transactions.get(cID, {}).values()), False)


def commandIDThread(cm,ret):
    ret.append(cm.getCommandID())
    return ret
