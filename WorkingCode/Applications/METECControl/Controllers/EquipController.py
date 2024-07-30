from Applications.METECControlv2.Readers.LabJack.LJReader import LabJack


class PadCtrl():
    def __init__(self, padName):
        self.ljConfig = None
        self.labjackReader = LabJack('LabJack')
        self.readerConfig = None
        self.routingConfig = None
        self.resources = None

    def openValves(self):
        pass

    def closeValve(self):
        pass

    def closeAllValves(self):
        pass

    def eStop(self):
        pass

def main():
    ctrl = PadCtrl()


if __name__ == '__main__':
    main()