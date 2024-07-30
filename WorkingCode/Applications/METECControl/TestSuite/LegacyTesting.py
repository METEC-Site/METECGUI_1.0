import json
import logging
import os
import time

from Framework.BaseClasses import Commands
from Framework.BaseClasses.Destination import Destination
from Framework.BaseClasses.Worker import Worker

TEST = './SiteTests/EPA_Test_1_Full_Site_SHORT.json'
BASE_DIR = os.path.abspath(os.path.join(__file__, "../../../../../CommandFramework"))
archiveTemplate = "test/Legacy_Site_Operation_Test_%Y%m%d"
READ_INTERVAL = 1


class LegacyTester(Destination, Worker, Commands.CommandClass):
    def __init__(self, name="legacyTester", archiver=None, commandManager=None, dataManager=None, eventManager=None,
                 **kwargs):
        Destination.__init__(self, name=name)
        Worker.__init__(self, archiver, commandManager, dataManager, eventManager, name)
        Commands.CommandClass.__init__(self, name=name)
        self.name = name
        self.CommandManager = None

    def emit(self, package):
        self._emitCommand(package)

    def runTest(self, testJson=TEST, indefinite = False):
        if testJson is None:
            testJson = "/".join([os.path.abspath(os.path.dirname(__file__)), TEST])
        if not type(testJson) is dict:
            try:
                with open(testJson) as file:
                    testJson = json.load(file)
            except Exception as e:
                logging.log(level=logging.DEBUG, msg="Unable to run test, unexpected field in testJson field. Error {}".format(e))
                return False
        # if not self.commandManager:
        #     logging.log(level=logging.DEBUG, msg='Unable to run test; No command manager set for Test Manage: {}'.format(self.name))
        #     return False
        if 'metadata' in testJson.keys():
            metadata = testJson['metadata']
            # log the metadata
            pass
        if 'startup' in testJson.keys():
            self.executeActions(testJson['startup'])
        if 'program' in testJson.keys():
            # TODO: stop execution immediately after self.terminate interrupt signal.
            self.executeActions(testJson['program'])
        if 'shutdown' in testJson.keys():
            self.executeActions(testJson['shutdown'])

    @Commands.CommandMethod
    def executeActions(self, functionality):
        actionTypeStart = functionality['actionType']
        timeDeltaStart = functionality['timeDelta']
        loopCountStart = functionality['loopCount']
        actions = functionality['actions']
        time.sleep(timeDeltaStart)
        for singleAction in actions:
            actionType = singleAction['actionType']
            timeDelta = singleAction['timeDelta']
            action = singleAction['action']
            operand = singleAction['operand']
            command = action
            time.sleep(timeDelta)
            # package = self.CommandManager.createCommandPackage(self.name, "executeActions", self.name, command, operand, {})
            # self.emit(package)