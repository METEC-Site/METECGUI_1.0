import os
import time

from Framework.BaseClasses.Commands import CommandClass
from Framework.BaseClasses.Metadata import Metadata
from Framework.BaseClasses.Readers.IntervalReader import IntervalReader
from Framework.BaseClasses.Subscriber import Subscriber
from Utils import FileUtils as fUtils

readerConfigPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../Config/SiteMetadata/GSH-1-Reader.json"))
edgeConfigPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../Config/SiteMetadata/CBs/GSH-1-Edges.json"))
LJIP = "10.1.106.188"


class GSHController(IntervalReader, CommandClass, Subscriber):
    def __init__(self, archiver, commandManager, dataManager, eventManager, GSHName, readerConfigPath, edgeConfigPath, nodeConfigPath):
        IntervalReader.__init__(self, GSHName, dataManager)
        CommandClass.__init__(self, GSHName, commandManager)
        Subscriber.__init__(self, GSHName, archiver, commandManager, dataManager, eventManager)

        self.ljConfig = None
        self.readerConfig = None
        self.routingConfig = None
        self.resources = None
        self.LJname = '.'.join([GSHName, 'LJ-1'])

        self.readConfig = self._loadReaderConfig(readerConfigPath)

        self.labjackReader = LabJack(self.LJname, IP=LJIP, readPinInfo=self.readConfig)
        self._loadEdges(edgeConfigPath)
        self._loadNodes(nodeConfigPath)
        self.metadata = self.mdFromReaderConfig(self.readConfig)

    ########################################################################################
    ####################### Methods for loading external information  ######################
    ########################################################################################

    def _loadReaderConfig(self, readerConfig):
        readerDict = fUtils.loadJson(readerConfig)
        return readerDict

    def mdFromReaderConfig(self, readerConfig):
        """ from a reader config json, extract all the fields and their information into a Metadata object."""
        md = {}
        for fieldName, fieldInfo in readerConfig.items():
            componentType = fieldInfo['component_type']
            if not componentType in COMPONENT_HANDLE_DICTIONARY:
                raise Exception(f'Unrecognized component type {componentType}, must be one of [{", ".join(COMPONENT_HANDLE_DICTIONARY.keys())}]')
            getMDMethod = COMPONENT_HANDLE_DICTIONARY[componentType]['makeMD']
            allFields = getMDMethod(self, fieldName, fieldInfo)
            for parsedFieldName, fieldMD in allFields.items():
                md[parsedFieldName] = fieldMD
        MD = Metadata(source='string', timestamp="datetime - UTC epoch", **md)
        return MD

    def _loadEdges(self, edgeConfig):
        i = -10
        pass

    ########################################################################################
    ############## Methods for interacting with external Framework Objects. ################
    ########################################################################################
    def handlePackage(self, package):
        pass

    def read(self):
        reading = self.labjackReader.read()

    def getReaderMetadata(self, sourceName=None):
        ljMetadata = None

    ########################################################################################
    ###################### Methods for extracting metadata from fields #####################
    ########################################################################################

    def _mdFromShutoff(self, fieldName, fieldInfo):
        return {}

    def _mdFromTC(self, fieldName, fieldInfo):
        return {}

    def _mdFromPT(self, fieldName, fieldInfo):
        return {}

    def _mdFromFM(self, fieldName, fieldInfo):
        return {}

    def _mdFromPROX(self, fieldName, fieldInfo):
        return {}

    ########################################################################################
    ######################### Methods for handling data from fields ########################
    ########################################################################################

    def _handleShutoff(self, fieldName, data):
        pass

    def _handleTC(self, fieldName, data):
        pass

    def _handlePT(self, fieldName, data):
        pass

    def _handleFM(self, fieldName, data):
        pass

    def _handlePROX(self, fieldName, data):
        pass

COMPONENT_HANDLE_DICTIONARY = {
    "shutoff": {"makeMD":GSHController._mdFromShutoff, "handler":GSHController._handleShutoff},
    "thermocouple": {"makeMD":GSHController._mdFromTC, "handler":GSHController._handleTC},
    "pressure_transducer": {"makeMD":GSHController._mdFromPT, "handler":GSHController._handlePT},
    "flowmeter": {"makeMD":GSHController._mdFromFM, "handler":GSHController._handleFM},
    "proximity_sensor": {"makeMD":GSHController._mdFromPROX, "handler":GSHController._handlePROX}
}


def main():
    gsh1 = GSHController(None, None, None, None, 'GSH-1', readerConfigPath, edgeConfigPath, nodeConfigPath)
    while True:
        print(gsh1.labjackReader.read())
        print("TC: " + str(gsh1.labjackReader.readSingleField('GSH-1.TC-2')))
        print("EV: " + str(gsh1.labjackReader.readSingleField('GSH-1.EV-1')))
        time.sleep(1)



if __name__ == '__main__':
    main()