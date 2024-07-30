import logging
import math
import signal
import sys

from PyQt5 import QtWidgets as qtw, QtCore as qtc
from PyQt5.QtCore import QPointF, QTimer
from PyQt5.QtGui import QPolygonF


def drawPolygon(painter, points, scale=1, xyorigin=[0 ,0], rotateDegrees=0):
    endPoints = []
    for x ,y in points:
        r, theta = toPolar(x, y)
        theta = theta + (rotateDegrees /180*math.pi)
        x, y = toCartesian(r, theta)
        x, y = (x *scale + xyorigin[0]), (y *scale + xyorigin[1])
        endPoints.append(QPointF(x, y))
    polygon = QPolygonF(endPoints)
    painter.drawPolygon(polygon)


def toCartesian(r, theta):
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    return x, y


def toPolar(x, y):
    r = math.sqrt(x ** 2 + y ** 2)
    theta = math.atan2(y, x)
    return r, theta


def getApp():
    app = qtw.QApplication.instance()
    if not qtw.QApplication.instance():
        app = qtw.QApplication(sys.argv)
    return app

class StartApp:
    def __init__(self, *args, **kwargs):
        self.timer=QTimer()
        self.app = getApp()
        self.startTimer = True

    def start(self):
        # timer to allow main loop to listen for events, like keyboard interrupts.
        signal.signal(signal.SIGINT, self.interruptHandler)

        def qt_exception_hook(exctype, value, traceback):
            # Print the error and traceback
            print(exctype, value, traceback)
            # Call the normal Exception hook after
            sys._excepthook(exctype, value, traceback)
            sys.exit(1)

        # Back up the reference to the exceptionhook
        sys._excepthook = sys.excepthook

        # Set the exception hook to our wrapping function
        sys.excepthook = qt_exception_hook
        try:
            logging.info("Starting Main App")
            qHeartbeat = QTimer()
            qHeartbeat.timeout.connect(lambda: None)
            qHeartbeat.setInterval(500)
            qHeartbeat.setSingleShot(False)
            qHeartbeat.start()
            self.app.exec_()
        except KeyboardInterrupt:
            logging.error('Keyboard interrupt handled from GUI, exiting program.')
        except Exception as e:
            logging.error(e)
        self.startTimer = False
        # stopper = ObjectManager.getStopper()
        # stopper.set()

    def interruptHandler(self, signum, frame):
        self.app.quit()

    def interpTimer(self, timeout, func):
        def timerEvent(self):
            try:
                func
            finally:
                if self.startTimer:
                    QTimer.singleShot(timeout, timerEvent)
        timerEvent(self)


class CustomQTLock():
    def __init__(self):
        self.lock = qtc.QMutex(mode=qtc.QMutex.Recursive)

    def __enter__(self):
        self.lock.lock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.unlock()


class StopThread(qtc.QThread):
    def __init__(self, method, passedArgs, activeThreadDict):
        qtc.QThread.__init__(self)
        self.method = method
        self.passedArgs = passedArgs
        self.activeThreads = activeThreadDict

    def run(self):
        self.method(*self.passedArgs)
        self.activeThreads.pop(self, None)