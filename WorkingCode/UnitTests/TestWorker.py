import json
import os
import tempfile
import unittest

from Framework.Archive.DirectoryArchiver import DirectoryArchiver
from Framework.BaseClasses.Worker import Worker
from Framework.Manager.DataManager import DataManager
from UnitTests import TestAll as TA


class WorkerConfig(Worker):
    def __init__(self, archiver=None, commandManager=None, datamanager=None, eventManager=None, name=None, CONFIG_STRING=None):
        Worker.__init__(self, archiver, commandManager, datamanager, eventManager, name)
        self.cfg = archiver.readConfig(CONFIG_STRING)

    def start(self):
        pass

    def end(self):
        pass

    def accept(self, package):
        pass

    def handlePackage(self, package):
        pass

CONFIG_FILENAME1 = "config1.cfg"
CONFIG_FILE1_CONTENTS = "Temp File Contents"

CONFIG_FILENAME2 = 'config2.json'
CONFIG_FILE2_CONTENTS = {
    "a": 1,
    "b": "b"
}


class TestWorker(unittest.TestCase):

    @TA.CleanNamespace('test_configImport')
    def test_configImport(self):
        with tempfile.TemporaryDirectory() as tdir:
            cfg1Path = os.path.join(tdir, CONFIG_FILENAME1)
            with open(cfg1Path, 'w') as f:
                f.write(CONFIG_FILE1_CONTENTS)

            cfg2Path = os.path.join(tdir, CONFIG_FILENAME2)
            with open(cfg2Path, 'w') as f:
                json.dump(CONFIG_FILE2_CONTENTS, f)

            CONFIG_FILE1_CHANNEL = {'channel': 'CFG-A', 'basePath': tdir, 'subPath': '', 'fileName': CONFIG_FILENAME1}
            CONFIG_FILE2_CHANNEL = {'channel': 'CFG-B', 'basePath': tdir, 'subPath': '', 'fileName': CONFIG_FILENAME2}
            with DirectoryArchiver('DirectoryArchiver', tdir, configFiles=[CONFIG_FILE1_CHANNEL, CONFIG_FILE2_CHANNEL]) as da:
                dm = DataManager(archiver=da, name='DataManager')
                wa1 = WorkerConfig(archiver=da, datamanager=dm, name='WorkerA1', CONFIG_STRING='CFG-A')
                self.assertEqual(wa1.cfg, CONFIG_FILE1_CONTENTS)

                wb1 = WorkerConfig(archiver=da, datamanager=dm, name='WorkerB1', CONFIG_STRING='CFG-B')
                self.assertEqual(wb1.cfg, json.dumps(CONFIG_FILE2_CONTENTS))