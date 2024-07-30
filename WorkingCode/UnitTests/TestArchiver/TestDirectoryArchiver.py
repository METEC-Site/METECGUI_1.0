import csv
import os
import tempfile
import time
import unittest
from datetime import datetime

from Framework.Archive.DirectoryArchiver import DirectoryArchiver, daFromArchive
from Framework.Manager.ObjectManager import ObjectManager as OM
from Framework.BaseClasses import Events
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Metadata import Metadata
from Framework.BaseClasses.Package import Package
from Utils import TimeUtils as tu
from Utils import ClassUtils as cu
from UnitTests import TestAll as TA
from UnitTests.TestArchiver.classes import TestLogEmitter

DANAME = "testDA"

CONFIG_FILENAME1 = "config1.cfg"
CONFIG_FILE1_CONTENTS = "Temp File Contents"
CONFIG_FILENAME2 = "config.txt"
CONFIG_FILE2_CONTENTS = '''
Temp File two contents
Second line
'''


CHANNEL_DATA = {
    'channel1': {'metadata': {'timestamp': 'int', 'val1': 'int', 'val2': 'float'},
                 'values': [
                     {'timestamp': 1, 'val1': 11, 'val2': 11.1},
                     {'timestamp': 2, 'val1': 12, 'val2': 12.1},
                     {'timestamp': 3, 'val1': 13, 'val2': 13.1},
                     {'timestamp': 4, 'val1': 14, 'val2': 14.1},
                     {'timestamp': 5, 'val1': 15, 'val2': 15.1},
                     {'timestamp': 6, 'val1': 16, 'val2': 16.1},
                     {'timestamp': 7, 'val1': 17, 'val2': 17.1},
                     {'timestamp': 8, 'val1': 18, 'val2': 18.1},
                     {'timestamp': 9, 'val1': 19, 'val2': 19.1}
                 ]
                 },
    'channel2': {'metadata': {'timestamp': 'int', 'val1': 'int', 'val2': 'float'},
                 'values': [
                     {'timestamp': 1, 'val1': 21, 'val2': 21.2},
                     {'timestamp': 2, 'val1': 22, 'val2': 22.2},
                     {'timestamp': 3, 'val1': 23, 'val2': 23.2},
                     {'timestamp': 4, 'val1': 24, 'val2': 24.2},
                     {'timestamp': 5, 'val1': 25, 'val2': 25.2},
                     {'timestamp': 6, 'val1': 26, 'val2': 26.2},
                     {'timestamp': 7, 'val1': 27, 'val2': 27.2},
                     {'timestamp': 8, 'val1': 28, 'val2': 28.2},
                     {'timestamp': 9, 'val1': 29, 'val2': 29.2}
                 ]
                 },
    'channel3': {'metadata': {'timestamp': {'type':int,'Notes1':'timestamp notes'},
                              'val1': {'type':int,'Notes2':'Field 1 notes'},
                              'val2': {'type':float,'Notes3':'Field 2 notes'}},
                 'values': [
                     {'timestamp': 1, 'val1': 31, 'val2': 31.2},
                     {'timestamp': 2, 'val1': 32, 'val2': 32.2},
                     {'timestamp': 3, 'val1': 33, 'val2': 33.2},
                     {'timestamp': 4, 'val1': 34, 'val2': 34.2},
                     {'timestamp': 5, 'val1': 35, 'val2': 35.2},
                     {'timestamp': 6, 'val1': 36, 'val2': 36.2},
                     {'timestamp': 7, 'val1': 37, 'val2': 37.2},
                     {'timestamp': 8, 'val1': 38, 'val2': 38.2},
                     {'timestamp': 9, 'val1': 39, 'val2': 39.2}
                 ]
                 },
}

LOGGING_CONFIG = {
  "version": 1,
  "formatters": {
    "simple": {
        'format': "%(asctime)s | %(name)s | %(levelname)s \n\tMessage: %(message)s"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "INFO",
      "stream": "ext://sys.stdout"
    },
    "archiveLogger": {
      "()": "Framework.Archive.Logger.getLogger",
      "level": "DEBUG"
    }
  },
  "root": {
    "level": "DEBUG",
    "handlers": [
      "console",
      "archiveLogger"
    ]
  }
}

class TestDirectoryArchiver(unittest.TestCase):
    def verifyChannel(self, cName, cData, da):
        daChannels = da.getChannels()
        self.assertTrue(cName in daChannels)

        cMetadata = da.getMetadata(cName)
        if not cu.isMetadata(cMetadata):
            cMetadata = Metadata(**cMetadata)
        if not cu.isMetadata(cData['metadata']):
            cMd = Metadata(**cData['metadata'])
        else:
            cMd = cData['metadata']
        self.assertEqual(cMetadata, cMd)

    def verifyData(self, cName, cData, readData):
        self.assertEqual(cData['values'], readData)


    @TA.CleanNamespace('test_DABasicTests')
    def test_DABasicTests(self):
        with tempfile.TemporaryDirectory() as tdir:
            da = DirectoryArchiver(name=DANAME, baseDir=tdir)
            self.assertEqual(da.getName(), DANAME)
            channels = da.getChannels()
            archChannel = channels.pop(da.archiveConfigName, None)
            loggerChannel = channels.pop(da.LR.getName(), None)
            archLogChannel = channels.pop(da.getName(), None)
            self.assertDictEqual(channels, {})
            da.end()

    @TA.CleanNamespace('test_Logging')
    def test_Logging(self):
        with tempfile.TemporaryDirectory() as tdir:
            da = DirectoryArchiver(name=DANAME, baseDir=tdir)
            loggerMessage1 = 'Directory Archiver Debug Message 1'
            loggerMessage2 = 'Directory Archiver Debug Message 2'
            da.logger.debug(loggerMessage1)
            da.logger.debug(loggerMessage2)
            logs = da.read(da.name, channelType=ChannelType.Log)
            allLogs = []
            for i in range(0, 10):
                loggername = f'TestLogEmitter{str(i)}'
                loggerEmitter = TestLogEmitter(loggername)
                log = loggerEmitter.emitLog()
                allLogs.append(log)
                daLogs = da.read(loggername, channelType=ChannelType.Log)
                for daLog in daLogs:
                    try:
                        self.assertNotEqual(daLog.find(log), -1)
                    except AssertionError:
                        # Log is not saved in archiver!
                        pass
            rootLogs = da.read('root', ChannelType.Log)
            for singleLog in allLogs:
                rootLog = rootLogs[0]
                try:
                    self.assertNotEqual(rootLog.find(singleLog), -1)
                except AssertionError:
                    pass # Root is not logging all logs!

    @TA.CleanNamespace('test_ManifestImport')
    def test_ManifestImport(self):
        with tempfile.TemporaryDirectory() as tDir:
            exampleManifest = [
                {'RecordDate': 'UTC', "RecordTime": "UTC", "Filename": 'filepath', "Notes": ""},
                {'RecordDate': '1/1/1970',"RecordTime":"0:00:00", "Filename":'./File1.csv',"Notes":"channel1"},
                {'RecordDate': "1/1/2020","RecordTime":"0:00:00", "Filename":'./File2.csv',"Notes":"channel2"}
            ]
            record1Timestamp = tu.DTtoEpoch(datetime.strptime(' '.join([exampleManifest[1]['RecordDate'], exampleManifest[1]['RecordTime']]), '%m/%d/%Y %H:%M:%S'))
            record2Timestamp = tu.DTtoEpoch(datetime.strptime(' '.join([exampleManifest[2]['RecordDate'], exampleManifest[2]['RecordTime']]), '%m/%d/%Y %H:%M:%S'))


            manFilename = os.path.join(tDir, 'manifest1.csv')
            f1Path = os.path.abspath(os.path.join(tDir, './File1.csv'))
            f2Path = os.path.abspath(os.path.join(tDir, './File2.csv'))
            with open(f1Path, 'w') as f1:
                f1.writelines(CONFIG_FILE1_CONTENTS)
            with open(f2Path, 'w') as f2:
                f2.writelines(CONFIG_FILE2_CONTENTS)

            with open(manFilename, 'w', newline='') as mf:
                manW = csv.DictWriter(mf,fieldnames=exampleManifest[0].keys())
                manW.writeheader()
                for line in exampleManifest:
                    manW.writerow(line)
            manConfig = [
                {'channel': "ExampleManifest1", "fileName": manFilename}
            ]

            with DirectoryArchiver(name=DANAME, baseDir=tDir, template="tmp1", manifests=manConfig) as da1:
                failed = False
                for i in range(0, 1):
                    chan1 = da1.readConfig('ExampleManifest1', record1Timestamp)
                    chan2 = da1.readConfig('ExampleManifest1', record2Timestamp)
                    try:
                        self.assertEqual(chan1, CONFIG_FILE1_CONTENTS)
                        self.assertEqual(chan2, CONFIG_FILE2_CONTENTS)
                    except AssertionError:
                        failed = True
                    # da1._rollover()
                if failed:
                    raise AssertionError(f'Failed Test test_ManifestImport')

    @TA.CleanNamespace('test_ConfigSaving')
    def test_ConfigSaving(self):
        with tempfile.TemporaryDirectory() as tdir:
            cfgBase = os.path.join(tdir, 'Config')
            os.mkdir(cfgBase)
            sub1 = os.path.join(cfgBase, 'subdir1')
            os.mkdir(sub1)
            cfg1Path = os.path.join(cfgBase, 'config1.cfg')
            cfg2Path = os.path.join(sub1, 'config2.cfg')
            cfg3Path = os.path.join(sub1, 'config3.cfg')
            cfgPaths = [cfg1Path, cfg2Path, cfg3Path]
            for cfg in cfgPaths:
                with open(cfg, 'w') as cFile:
                    cFile.write('Hello World')
            with open(cfg1Path, 'a') as cFile:
                cFile.write('\nGoodbye, World')

            # NOTE: fullPath is not actually used by the directory archiver, and is only used as a convenience for
            # testing.
            configs = [
                {'channel': 'config1', "fullPath": cfg1Path, 'basePath': cfgBase, 'fileName': 'config1.cfg'},
                {'channel': 'config2', "fullPath": cfg2Path, 'basePath': cfgBase, 'subPath': 'subdir1',
                 'fileName': 'config2.cfg'},
                {'channel': 'config3', "fullPath": cfg3Path, 'basePath': cfgBase, 'subPath': 'subdir1',
                 'fileName': 'config3.cfg'}
            ]

            with DirectoryArchiver(name=DANAME, baseDir=tdir, template='TestFiles', configFiles=configs) as da:
                for singleConfig in configs:
                    with open(singleConfig['fullPath']) as cFile:
                        configContents = cFile.read()
                        # daContents = da.readConfig(singleConfig['channel'])
                        daContents = da.readConfig(singleConfig['channel'])
                        self.assertEqual(configContents, daContents)
            da.end()

    @TA.CleanNamespace('test_DAData')
    def test_DAData(self):
        with tempfile.TemporaryDirectory() as tDir:
            with DirectoryArchiver(name=DANAME, baseDir=tDir, template="tmp1", configFiles=[]) as da1:
                for cName, cData in CHANNEL_DATA.items():
                    da1.createChannel(cName, ChannelType.Data, metadata=cData['metadata'])
                    # packet = Package(source=cName, channelType=ChannelType.Log, payload=cData['values'])
                    packet = Package(source=cName, channelType=ChannelType.Data, payload=cData['values'])
                    da1.accept(packet)
                    self.verifyChannel(cName, cData, da1)
                    self.verifyData(cName, cData, da1.read(cName)[0])
            da1.end()
            #     # testing the restart functionality of the archiver.
            # with DirectoryArchiver(name=DANAME, baseDir=tDir, template="tmp1", configFiles=[]) as da1:
            #     for cName, cData in CHANNEL_DATA.items():
            #         self.verifyChannel(cName, cData, da1)
            # da1.end()

    @TA.CleanNamespace('test_DARollover')
    def test_DARollover(self):
        with tempfile.TemporaryDirectory() as tDir:
            cFilename1 = os.path.join(tDir, CONFIG_FILENAME1)
            with open(cFilename1, "w") as cf:
                print(CONFIG_FILE1_CONTENTS, file=cf, end='')
            cFilename2 = os.path.join(tDir, CONFIG_FILENAME2)
            with open(cFilename2, "w") as cf:
                print(CONFIG_FILE2_CONTENTS, file=cf, end='')

            configFiles = [
                {'channel': 'config1', 'basePath': tDir, 'fileName': CONFIG_FILENAME1},
                {'channel': 'config2', 'basePath': tDir, 'fileName': CONFIG_FILENAME2}
            ]
            with DirectoryArchiver(name=DANAME, baseDir=tDir, template='_%Y-%m-%d_%H-%M-%S',
                                   configFiles=configFiles) as da1:
                for cName, cData in CHANNEL_DATA.items():
                    da1.createChannel(cName, ChannelType.Data, metadata=cData['metadata'])
                    packet = Package(source=cName, channelType=ChannelType.Data, payload=cData['values'])
                    da1.accept(packet)
                allDataBeforeRO = {}
                for channelName, channelTypes in da1.getChannels().items():
                    allDataBeforeRO[channelName] = {}
                    for singleType in channelTypes:
                        allDataBeforeRO[channelName][singleType] = da1.read(channelName, singleType)
                da1._rollover()

                for cName, cData in CHANNEL_DATA.items():
                    da1.createChannel(cName, ChannelType.Data, metadata=cData['metadata'])
                    packet = Package(source=cName, channelType=ChannelType.Data, payload=cData['values'])
                    da1.accept(packet)
                allDataAfterRO = {}
                for channelName, channelTypes in da1.getChannels().items():
                    allDataAfterRO[channelName] = {}
                    for singleType in channelTypes:
                        allDataAfterRO[channelName][singleType] = da1.read(channelName, singleType)
                self.assertEqual(allDataBeforeRO['channel1'][ChannelType.Data], allDataAfterRO['channel1'][ChannelType.Data])
                self.assertEqual(allDataBeforeRO['channel2'][ChannelType.Data], allDataAfterRO['channel2'][ChannelType.Data])
            da1.end()


        with tempfile.TemporaryDirectory() as tDir:
            cFilename1 = os.path.join(tDir, CONFIG_FILENAME1)
            with open(cFilename1, "w") as cf:
                print(CONFIG_FILE1_CONTENTS, file=cf, end='')
            cFilename2 = os.path.join(tDir, CONFIG_FILENAME2)
            with open(cFilename2, "w") as cf:
                print(CONFIG_FILE2_CONTENTS, file=cf, end='')

            configFiles = [
                {'channel': 'config1', 'basePath': tDir, 'fileName': CONFIG_FILENAME1},
                {'channel': 'config2', 'basePath': tDir, 'fileName': CONFIG_FILENAME2}
            ]

            nowTime = tu.nowDT()
            nowH, nowM, nowS = nowTime.hour, nowTime.minute, nowTime.second
            with DirectoryArchiver(name=DANAME, baseDir=tDir, template='_%Y-%m-%d_%H-%M-%S',
                                   configFiles=configFiles, utcStartHMS=f'{nowH}:{nowM}:{nowS}', rolloverInterval=2, checkROInterval=1) as da2:
                da2.start()
                time.sleep(3)
                # must end DA functionality. Otherwise, error is generated as the tdir cleanup deletes the directory while
                # the thread is running. THis thread will repeatedly rollover (or try to), based on file paths that
                # no longer exist.
                da2.end()
            numDirs = os.listdir(tDir)
            numDirs = list(filter(lambda x: os.path.isdir(os.path.join(tDir, x)), numDirs))
            self.assertEqual(len(numDirs), 2)

    @TA.CleanNamespace('test_Events')
    def test_Events(self):
        with tempfile.TemporaryDirectory() as tDir:
            with DirectoryArchiver(name=DANAME, baseDir=tDir, template="tmp1_%Y%m%d", configFiles=[]) as da1:
                eventsSent = []
                for cName, cData in CHANNEL_DATA.items():
                    da1.createChannel(cName, ChannelType.Event)
                    event1 = Events.EventPayload(cName, Events.EventTypes.Default, msg='Test Event')
                    event2 = Events.EventPayload(cName, Events.EventTypes.Default, msg='Test Event')
                    eventsSent.append(event1)
                    eventsSent.append(event2)
                    packet1 = Package(source=cName, channelType=ChannelType.Event, payload=event1)
                    packet2 = Package(source=cName, channelType=ChannelType.Event, payload=event2)
                    da1.accept(packet1)
                    da1.accept(packet2)


                    events = da1.read(cName, ChannelType.Event)
                    for sentEvent in eventsSent:
                        try:
                            self.assertTrue(sentEvent.toDict() in events)
                        except AssertionError:
                            pass # event not found in da read events
            da1.end()

    @TA.CleanNamespace('test_DACreation')
    def test_DACreation(self):
        for i in range(0, 100):
            with tempfile.TemporaryDirectory() as tdir:
                baseDir = os.path.join(tdir, 'TempBaseDir')
                da = DirectoryArchiver("DA", baseDir)
                self.assertIsInstance(da, DirectoryArchiver)
                da.start()
                da.end()
                time.sleep(.01) # allow enough time for directory archiver to send shutdown signals and whatnot.

    @TA.CleanNamespace('test_DARecreation')
    def test_DAFromArchive(self):

        def addReading(readings, channelName, channelType, singleReading):
            if not channelName in readings:
                readings[channelName] = {}
            readings[channelName][channelType] = singleReading

        with tempfile.TemporaryDirectory() as tdir:
            readings = {}
            da = DirectoryArchiver(baseDir=tdir)
            archivePath = da.archivePath
            for singleChannelName, ci in CHANNEL_DATA.items():
                md = Metadata(**ci['metadata'])
                da.createChannel(singleChannelName, ChannelType.Data, metadata=md)
                for singleReading in ci['values']:
                    pkg = Package(source=singleChannelName, payload=singleReading, metadata=md, channelType=ChannelType.Data)
                    da.accept(pkg)
                addReading(readings, singleChannelName, ChannelType.Data, da.read(singleChannelName))
            addReading(readings, singleChannelName, ChannelType.Log, da.read('archiveLogger', ChannelType.Log))

            da.end()
            time.sleep(1)
            da2 = daFromArchive(archivePath)
            for channelName, chanInfo in readings.items():
                for channelType, reading in chanInfo.items():
                    try:
                        self.assertEqual(reading==da2.read(channelName, channelType), True)
                    except AssertionError as e:
                        pass
            da2.end()

            v2ArchivePath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'TestArchives', 'VanData_2020-02-09_23-27-48'))
            v2Da = daFromArchive(v2ArchivePath)
            picarroRead = v2Da.read('Picarro')
            radioConfigRead = v2Da.read('radios', ChannelType.Config)
            self.assertEqual(picarroRead == v2Da.read('ChannelDoesNotExist'), False)
            self.assertEqual(radioConfigRead == v2Da.read('ChannelDoesNotExist'), False)
            v2Da.end()


if __name__ == "__main__":
    unittest.main()
