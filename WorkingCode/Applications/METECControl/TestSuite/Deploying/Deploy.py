import json
import logging
import pathlib
import threading
from enum import Enum, auto

from PyQt5 import QtCore as qtc, QtWidgets as qtw
from Utils import QtUtils as qtu
from Utils import TimeUtils as tu
from Utils.ExperimentUtils import ExperimentParser as EParse
from Utils.QtUtils import CustomQTLock

EXP_ID_TXT_FILE = pathlib.Path(pathlib.Path(__file__).parent).joinpath("EXP_ID_TRACKER.txt")
EXP_ID_LOCK = threading.RLock()
GLOBAL_EXPERIMENT_TIME_BUFFER_OFFSET = 1

def LOAD_EXP_ID():
    """Load the experiment ID from the """
    with EXP_ID_LOCK:
        try:
            with open(EXP_ID_TXT_FILE, "r", newline="\n") as f:
                dt = tu.EpochtoDT(float(f.readline()))
                id = int(f.readline())
        except:
            dt = tu.nowDT()
            id = 1
        return dt, id

def DUMP_EXP_ID(DT, ID):
    with EXP_ID_LOCK:
        with open(EXP_ID_TXT_FILE, "w", newline="\n") as f:
            f.writelines("\n".join([str(tu.DTtoEpoch(DT)), str(ID)]))

class _TestPeriods(Enum):
    precal = auto()
    experiment = auto()
    postcal = auto()
    expEnd = auto()

class TestStates(Enum):
    unstarted = auto()
    queued = auto()
    running = auto()
    cancelled = auto()
    finished = auto()

class TestScript(qtc.QObject):
    lastDate, expID = LOAD_EXP_ID()
    finished = qtc.pyqtSignal()
    cancelled = qtc.pyqtSignal()

    def __init__(self, GUIInterface=None, script={}):
        qtc.QObject.__init__(self)
        self.thread = qtc.QThread()
        self.timer = qtc.QTimer(self)
        self.moveToThread(self.thread)
        self.thread.started.connect(self.run)
        self.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.finished.connect(self.timer.stop)
        gshFlowMeters = list(script['Metadata']['FMConfig'].values())
        gasHousesInFMConfig = [int(gshFM.split('.')[0].split('-')[1]) for gshFM in gshFlowMeters]
        self.sources = list(set(gasHousesInFMConfig))  # Gas House/Process in a list from 0-4
        self.state = TestStates.unstarted
        self.app = qtu.getApp()

        self.GUIInterface=GUIInterface
        self.jsonScript = script
        self.parser = EParse(self.jsonScript)
        self.readers = self.getSourceReaders(self.jsonScript)
        self.eStop = False
        self.startTime = None

        self.timingList = []
        self.queue = []
        self.lock = CustomQTLock()
        self.timerCounter = 0
        self.expID = self.calcNewExpID()
        self.nextEventTimestamp = 0
        self.sectionOffset = 0
        self.iterOffset = 0
        self.hasFinished=False


    def calcNewExpID(self):
        with EXP_ID_LOCK:
            expDate = tu.nowDT() # UTC datetime of the event.
            if not expDate.date() == TestScript.lastDate.date():
                TestScript.lastDate = expDate
                TestScript.expID = 1
            expID = f"{TestScript.expID:03}"
            TestScript.expID += 1
            DUMP_EXP_ID(expDate, TestScript.expID)
            fullID = "".join([expDate.strftime("%Y%m%d"), expID])
            return int(fullID)

    def getState(self):
        return self.state

    def setQueued(self):
        self.state = TestStates.queued

    def setRunning(self):
        self.state = TestStates.running

    def setFinished(self):
        self.state = TestStates.finished
        self.timer.stop()
        self.hasFinished=True
        self.finished.emit()

    def setCancelled(self):
        self.state = TestStates.cancelled
        self.timer.stop()
        self.hasFinished=True

    def calculateTimings(self):
        self.sectionOffset=0
        self.iterOffset=0
        self.queue=[]
        # inital start time offset of first timer.
        self._scheduleMethodAndIncrement(self.doExpStart, self.nextEventTimestamp)

        if not self.parser.preExperiment is None:
            # schedule the precal notification right after experiment start.
            self._scheduleMethodAndIncrement(self.doCalStart, self.nextEventTimestamp)
            self.scheduleScript(self.parser.preExperiment)
            self._scheduleMethodAndIncrement(self.doCalEnd, self.nextEventTimestamp)# adding one second to allow for extra time between sections.

        self._scheduleMethodAndIncrement(self.doMainStart, self.nextEventTimestamp)
        self.scheduleScript(self.parser.experiment)
        self._scheduleMethodAndIncrement(self.doMainEnd, self.nextEventTimestamp) # adding one second to allow for extra time between sections.

        if not self.parser.postExperiment is None:
            self._scheduleMethodAndIncrement(self.doCalStart, self.nextEventTimestamp)
            self.scheduleScript(self.parser.postExperiment)
            self._scheduleMethodAndIncrement(self.doCalEnd, self.nextEventTimestamp)

        self._scheduleMethodAndIncrement(self.doExpEnd, self.nextEventTimestamp)

    def start(self):
        self.thread.start()
        self.app.exec()

    def run(self):
        self.calculateTimings()
        self.startAllTimers()
        self.setRunning()

    def doEmission(self, action):
        logging.info(f'Doing emission {action}')
        with self.lock:
            if not self.eStop:
                self.GUIInterface.emitEmissionEvent(self.expID, action)
                reader = action['Controller'] + ".LJ-1"
                for valve, state in action['SetStates'].items():
                    valve = action['Controller'] + "." + valve
                    self.commandValve(reader, valve, state)

    def doExpStart(self, action):
        self.startTime = tu.nowEpoch()
        logging.info(f'Doing experiment start: {self.expID}')
        with self.lock:
            self.GUIInterface.emitExpStart(self.expID, self.sources, self.jsonScript)

    def doCalStart(self, action):
        logging.info(f'Doing cal start: {self.expID}')
        with self.lock:
            self.GUIInterface.emitCalStart(self.expID, self.sources)

    def doCalEnd(self, action):
        logging.info(f'Doing cal end: {self.expID}')
        with self.lock:
            self.GUIInterface.emitCalEnd(self.expID, self.sources)

    def doMainStart(self, action):
        logging.info(f'Doing Main Start: {self.expID}')
        with self.lock:
            self.GUIInterface.emitMainStart(self.expID, self.sources)

    def doMainEnd(self, action):
        logging.info(f'Doing Main End: {self.expID}')
        with self.lock:
            self.GUIInterface.emitMainEnd(self.expID, self.sources)

    def doExpEnd(self, action):
        logging.info(f'Doing experiment end: {self.expID}')
        with self.lock:
            self.GUIInterface.emitExpEnd(self.expID, self.sources)
            self.setFinished()

    def incrementNextTimestamp(self, amount):
        self.nextEventTimestamp += amount

    def scheduleScript(self, script):
        iters = self.parser.getIterations(script)
        isCloseAfterSection = self.parser.isCloseAfterSection(script)
        isCloseAfterIter = self.parser.isCloseAfterIter(script)
        controlledReleases = self.parser.getControlledReleases(script)
        self.iterOffset = 0
        for i in range(0, iters):
            for event in controlledReleases:
                timing = event['Time']
                iterTiming = timing + self.iterOffset
                newTiming = iterTiming + self.sectionOffset
                timingDelta = newTiming-self.nextEventTimestamp
                for action in event['Actions']:
                    self._scheduleMethodAndIncrement(self.doEmission, newTiming, action)
                self.incrementNextTimestamp(timingDelta)
            if isCloseAfterIter:
                self._scheduleMethodAndIncrement(self.emitCloseAll, self.nextEventTimestamp)
            self.iterOffset = self.nextEventTimestamp - self.sectionOffset
        if isCloseAfterSection:
            self._scheduleMethodAndIncrement(self.emitCloseAll, self.nextEventTimestamp)
        self.sectionOffset = self.nextEventTimestamp

    def _scheduleMethodAndIncrement(self, method, startTime, action=None, increment=0):
        with self.lock:
            self.queue.append({"startTime": startTime, "method": method, "action": action})
            self.incrementNextTimestamp(increment)

    def checkQueue(self):
        checkedTime=tu.nowEpoch()
        tDelta = checkedTime-self.startTime # adding in *10 for debugging
        methodsNeedingDone=list(filter(lambda x: x['startTime'] < tDelta, self.queue))
        for methodInfo in methodsNeedingDone:
            self.queue.remove(methodInfo)
            methodInfo['method'](methodInfo['action'])

    def startAllTimers(self):
        self.timer.timeout.connect(self.checkQueue)
        self.startTime = tu.nowEpoch()
        self.timer.start(10) # check every 10 milliseconds.

    def cancelScript(self):
        with self.lock:
            self.eStop = True
            if self.state == TestStates.running:
                self.emitCloseAll()
                self.doExpEnd(None)
            self.setCancelled()

    def emitCloseController(self, readerName):
        valveNames = list(filter(lambda x: x['reader'] == readerName and x['item_type'] == 'ElectricValve',self.sensorRecord))
        for singleValve in valveNames:
            self.commandValve(readerName, singleValve, 1)

    def commandValve(self, readerName, valveName, value):
        if value == 1:
            # logging.info(f'Closing valve {valveName} from reader {readerName}')
            self.GUIInterface.closeValve(readerName, args=[valveName])
        else:
            # logging.info(f'Opening valve {valveName} from reader {readerName}')
            self.GUIInterface.openValve(readerName, args=[valveName])

    def emitCloseAll(self, action=None):
        for reader in self.readers:
            logging.info(f'Closing all for reader {reader}')
            self.GUIInterface.closeAllValves(reader)

    def getSourceReaders(self, script):
        parse = EParse(script)
        eps = parse.getEmissionPoints()
        readers = list(set(self.readerFromEP(ep) for ep in eps))
        return readers

    def readerFromEP(self, epName):
        # epRow = self.epRecord[epName]
        # readerName = "".join(["CB-",epRow['Pad'], epRow['Controller'], '.LJ-1'])# TODO: use a mapping instead of hard coding.
        readerName = "".join(['CB-', epName[:epName.index('-')], '.LJ-1'])
        return readerName


    # def levelsFromEP(self, reader, epName, epRow, ab, level):
    #     valveRows = list(filter(lambda x: x['reader'] == reader and x['item_type'] == 'Electric Valve',self.sensorRecord))
    #     valvesInRow = list(filter(lambda x: int(self.valveRowColFromName(x['name'])[0]) == int(epRow), valveRows))
    #     bString = self.intToInverseBinary(level)
    #
    #     # get the AB solenoid from the flow control valves.
    #     valvesInRow = sorted(valvesInRow, key = lambda x: x['name'])
    #     abValve = valvesInRow[-1]
    #     valvesInRow.remove(abValve)
    #
    #     valveLevels = {}
    #     for valveProps in valvesInRow:
    #         row, col = self.valveRowColFromName(valveProps['name'])
    #         valveLevels[valveProps['name']] = (1-self.colIsOn(bString, col)) # invert because 0 means to turn a valve on.
    #
    #     if ab == 'A':
    #         valveLevels[abValve['name']] = 1
    #     else:
    #         valveLevels[abValve['name']] = 0
    #     return valveLevels

    def intToInverseBinary(self, level):
        b = ""
        while level > 0:
            b += str(int((level)%2))
            level = int(level / 2)
        return b

    def colIsOn(self, bString, col):
        if len(bString) < col:
            return 0
        return int(bString[col-1])

    # def valveRowColFromName(self, valveName):
    #     spec, rowCol = valveName.split('EV-')
    #     row = int(rowCol[0])
    #     col = int(rowCol[1])
    #     return row, col

class ScriptWidget(qtw.QListWidgetItem):
    finished = qtc.pyqtSignal()

    def __init__(self, text=None, parent=None, json=None, script=None, fullPath=None, gsh=None):
        qtw.QListWidgetItem.__init__(self, text, parent)
        self.json = json
        self.script = script
        self.fullPath = fullPath
        self.gsh = gsh

    def getGasHouse(self):
        return self.gsh

if __name__ == '__main__':
    jsonPath = "C:\\Users\\METEC\\Documents\\SVN_METEC\\Operations\\AutomatedExperiments\\2022 CM Testing Pad 45\\Experiments\\Experiments for Week 1 and 2\\Exp_FM_config 3_Pressure_40psia\\30min_3EP_4T-32_38slpm_4W-31_1slpm_4S-44_5slpm_wPrecal_L.json"
    with open(jsonPath, 'r') as f:
        importedScript = json.load(f)
    importedScript['Experiment']['Iterations'] = 3
    importedScript['Experiment']['CloseAfterIteration'] = True
    scriptObject = TestScript(script=importedScript)
    scriptObject.start()
    print("exited")