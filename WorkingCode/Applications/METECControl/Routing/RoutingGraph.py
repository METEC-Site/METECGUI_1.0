import json
import logging
import os
from copy import deepcopy

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

volumesFolder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Config/SiteMetadata/VolumeRouting'))
controllerMappingPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Config/SiteMetadata/ControllerToGSH.json'))
EP_FILEPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Config/SiteMetadata/EPConfigs/ExampleEPConfig_20200428000000.xlsx'))

with open(controllerMappingPath) as cMapF:
    CTRL_TO_GSH = json.load(cMapF)

# todo:
#  1) Change/generate GSH-1.json to match the output of the Drawio.
#  2) Iterate through the controller boxes on each connection, checking that GSH-1 maps correctly to each one
#  3) Iterate through each gas house (2-4) and repeat steps 1-2

CONTROLLER_ROUTING = {}

for volumeFile in os.listdir(volumesFolder):
    # start here for changing which controller boxes are loaded in.
    with open(os.path.join(volumesFolder, volumeFile)) as vFile:
        volDict = json.load(vFile)
        ctrlName = volumeFile.split('-Edges')[0] # will split into two names: ['{ctrlName}', '.json'] only want {ctrlName}
        # if CTRL_TO_GSH.get(ctrlName) == 'GSH-1' or 'GSH-2' or 'GSH-3' or 'GSH-4':
        #     CONTROLLER_ROUTING[ctrlName] = volDict
        CONTROLLER_ROUTING[ctrlName] = volDict


class RoutingGraph():
    def __init__(self, volumeDict, epConfig):
        self.logger = logging.getLogger()

        self.edgesMaster = {}
        self.currentStates = {}
        self.masterGraph = nx.Graph()
        self.currentGraph = nx.Graph()


         # load the configs into the 'edgesMaster' dictionary
        self.loadMasterStates(volumeDict)
        self.loadEPConfig(epConfig)
        # after this, self.edgesMaster looks like a dictionary similar to the following:
        """
        {
            "item_name":
            {
            'volume': ***VOLUME INFORMATION***,
            'metadata': ***METADATA***
            }
        }
        """
        #
        # list(map(lambda x: self.masterG.add_node(x), self.edgesMaster.keys()))
        # for itemName, itemAttrs in self.edgesMaster.items():
        #     volume = itemAttrs.get('volume')
        #     if volume: #volume exists, and is mapped in the node network.
        #         for stateInfo in volume.get('STATES', []):
        #             for commonNode in stateInfo['COMMON']:
        #                 self.masterG.add_edge(itemName, commonNode, state=stateInfo['STATE'])
        #     else: # volume not found, so don't add it.
        #         pass
        # self.currentStates = {}
        # self.resetCurrent()
        #
        # ###########################################
        # ## Continue Refactoring after this line ###
        # ###########################################
        #
        # self.currentG = nx.Graph()

    ####################################################################################################################
    ######################################### Loading configs from files/dicts #########################################
    ####################################################################################################################

    def loadMasterStates(self, cbDict):
        """ load all the states from the controller box routing/mapping dictionary into this class.

        At the end of this method, will have all the edge states copied from """
        for cbName, cbEdges in cbDict.items():
            for singleEdge, edgeProperties in cbEdges.items(): # todo: check the difference between .keys(), .values(), .items()
                try:
                    self.currentStates[singleEdge] = None
                    self._addToEdges(singleEdge, edgeProperties)
                except Exception as e:
                    self.logger.info(f'Could not add edge {singleEdge} due to exception {e}')

    def loadEPConfig(self, epFilepath):
        epConfig = pd.read_excel(epFilepath)
        for row in epConfig.iterrows():
            # todo: Isabella, the error we were running into is that this version of the EP config has manual valves on CB-1W and other items on pad 1,
            #  but this change was not reflected in the volume routing or pnid's that are currently out there. This should be changed and updated to the
            #  newest version. Update: changes have been made on NodeConfigUtility and PnID's to reflect this.

            upstreamValveName, downstreamManualValve, emissionPoint = self._extractInfoFromRow(row[1])
            # todo: to fix this part, change the 'source to  one name but the volume name
            # todo:put the adding of nodes and edges within addBinaryValve method. Update: put adding of nodes and edges for EV in _addBinaryValve
            self._addBinaryValve(upstreamValveName) # adds upstream volumes, as well as downstream A/B volumes.
            if not downstreamManualValve == None:
                self._addBinaryValve(downstreamManualValve.get('Manual Valve')) # after this, the L/R volumes will be added.
                upstreamVol, lVol, rVol = self._getVolsFromName(downstreamManualValve.get('Manual Valve'))
                if emissionPoint.get('MV State') == "L":
                    self.masterGraph.add_node(emissionPoint.get('Emission Point'))
                    self.masterGraph.add_edge(lVol, emissionPoint.get('Emission Point'))
                elif emissionPoint.get('MV State') == "R":
                    self.masterGraph.add_node(emissionPoint.get('Emission Point'))
                    self.masterGraph.add_edge(rVol, emissionPoint.get('Emission Point'))
                elif emissionPoint.get('MV State') == None:
                    pass
            elif emissionPoint['EV State'] == 'A':
                upstreamVol, aVol, bVol = self._getVolsFromName(upstreamValveName)
                self.masterGraph.add_node(emissionPoint.get('Emission Point'))
                self.masterGraph.add_edge(aVol, emissionPoint.get('Emission Point'))
            elif emissionPoint['EV State'] == 'B':
                upstreamVol, aVol, bVol = self._getVolsFromName(upstreamValveName)
                self.masterGraph.add_node(emissionPoint.get('Emission Point'))
                self.masterGraph.add_edge(bVol, emissionPoint.get('Emission Point'))
    ####################################################################################################################
    ################################ Methods for adding nodes via volume/routing config ################################
    ####################################################################################################################

    def _addToEdges(self, edgeName, edgeProperties):
        componentType = edgeProperties['component_type']
        componentHandler = COMPONENT_HANDLERS[componentType]
        componentHandler(self, edgeName, edgeProperties)

    def _handleFlowValve(self, edgeName, edgeProperties):
        states = edgeProperties['states']
        self.edgesMaster[edgeName] = deepcopy(states)
        for state in states:
            source = state['source']
            destination = state['destination']
            self.masterGraph.add_node(source)
            self.masterGraph.add_node(destination)
            self.masterGraph.add_edge(source, destination)

    def _handleDirectionalValve(self, edgeName, edgeProperties):
        states = edgeProperties['states']
        self.edgesMaster[edgeName] = deepcopy(states)
        for state in states:
            for i in state['common_volumes']:
                self.masterGraph.add_node(i)
            for i in state['common_volumes']:
                for j in state['common_volumes']:
                    if not j == i:
                        self.masterGraph.add_edge(i, j)

    def _handleVolumeMeasurement(self, edgeName, edgeProperties):   #Q: wouldn't this be a method for adding nodes via the EP config?
        # todo: add functionality here.
        pass

    ####################################################################################################################
    ###################################### Methods for adding nodes via EP config ######################################
    ####################################################################################################################

    def _getVolsFromName(self, valveName):
        states = self.edgesMaster[valveName]
        stateA = list(filter(lambda x: x['state'] == 'A', states))[0]
        stateB = list(filter(lambda x: x['state'] == 'B', states))[0]

        commonVolumes = []
        stateAVolumes = []
        stateBVolumes = []
        for volume in set([*stateA['common_volumes'], *stateB['common_volumes']]):
            if volume in stateA['common_volumes'] and volume in stateB['common_volumes']:
                commonVolumes.append(volume)
            elif volume in stateB['common_volumes']:
                stateBVolumes.append(volume)
            elif volume in stateA['common_volumes']:
                stateAVolumes.append(volume)
        upstreamVol = commonVolumes[0]
        aVol = stateAVolumes[0]
        bVol = stateBVolumes[0]

        return upstreamVol, aVol, bVol

    # def _addDownstreamValve(self, upstreamValveName, downstreamManualValve, upstreamEVVolume, upstreamMVVolume, downstreamEVVolumeA, downstreamEVVolumeB, downstreamMVVolumeA, downstreamMVVolumeB):
    def _addBinaryValve(self, valveName):
        upstreamVol, aVol, bVol = self._getVolsFromName(valveName)

        ### from here down, refactor to use the variable names.
        self.masterGraph.add_node(upstreamVol)
        self.masterGraph.add_node(aVol)
        self.masterGraph.add_node(bVol)
        # self.masterGraph.add_edge(upstreamVol, aVol, name='valveName') #Other methods don't include name for edges. Necessary to add?
        # self.masterGraph.add_edge(upstreamVol, bVol, name='valveName')
        self.masterGraph.add_edge(upstreamVol, aVol, name=valveName)
        self.masterGraph.add_edge(upstreamVol, bVol, name=valveName)

        # todo: add functionality to add the downstream manual valve node to the master graph.

    def _extractInfoFromRow(self, dfRow):
        """
        dfRow: row extracted from dataframe with columns matching an EP Config.

        upstreamValveName: the full directional valve name (CB-XN.EV-YZ)
        downstreamManualValve: the full manual valve name - if any. (CB-XN.MV-Y, or None if doesn't exist.)
        emissionPoint: Full name of the emission point at the end of the routing.
        """

        #upstreamValveName:
        CBName = dfRow.at['CB']
        EVName = dfRow.at['EV']
        upstreamValveName = '.'.join([CBName, EVName])

        #downstreamManualValve:
        MVName = dfRow.at['MV']
        MVstates = ['Manual Valve','MV State']
        MVvalues = []
        if MVName and not MVName == '-' and not (not isinstance(MVName, str) and np.isnan(MVName)):
            MVvalues.append('.'.join([CBName, MVName]))
            if dfRow['MV State'] == 'R':
                MVvalues.append('R')
            else:
                MVvalues.append('L')
            downstreamManualValve = dict(zip(MVstates, MVvalues))
        else:
            downstreamManualValve = None

        #emissionPoint:
        EPstates = ['Emission Point','EV State','MV State']
        EPvalues = []
        EPvalues.append(dfRow.at['Emission Point'])
        if dfRow['EV State'] == 'A':
            EPvalues.append('A')
            if dfRow['MV'] and not dfRow['MV'] == '-':
                if dfRow['MV State'] == 'R':
                    EPvalues.append('R')
                else:
                    EPvalues.append('L')
            else:
                EPvalues.append('None')
        elif dfRow['EV State'] == 'B':
            EPvalues.append('B')
            if dfRow['MV'] and not dfRow['MV'] == '-':
                if dfRow['MV State'] == 'R':
                    EPvalues.append('R')
                else:
                    EPvalues.append('L')
            else:
                EPvalues.append('None')
        emissionPoint = dict(zip(EPstates,EPvalues))

        return upstreamValveName, downstreamManualValve, emissionPoint

    ####################################################################################################################
    ############################################# Graph interfacing methods ############################################
    ####################################################################################################################

    def showPath(self, source, dest):
        # look up this:
        # shortest_path from networkx documentation.
        if nx.has_path(self.masterGraph, source, dest):
            allPaths = nx.all_simple_paths(self.masterGraph, source, dest)
            newG = nx.Graph()
            for pathNodes in allPaths:
                for node in pathNodes:
                    if not node in newG.nodes:
                        newG.add_node(node)
                    for secondNode in pathNodes:
                        if not self.masterGraph.get_edge_data(node, secondNode, None) is None:
                            newG.add_edge(node, secondNode,  **self.masterGraph.get_edge_data(node, secondNode))
            plt.figure(figsize=(30, 30))
            nx.draw(newG, with_labels=True)
            plt.show()

    def shortestPath(self, source, dest):
        if nx.has_path(self.masterGraph, source, dest):
            shortestPath = nx.shortest_path(self.masterGraph, source, dest)
            newG = nx.Graph()
            for node in shortestPath:
                newG.add_node(node)
                for secondNode in shortestPath:
                    if not self.masterGraph.get_edge_data(node, secondNode, None) is None:
                        newG.add_edge(node, secondNode, **self.masterGraph.get_edge_data(node, secondNode))
            plt.figure(figsize=(30, 30))
            nx.draw(newG, with_labels=True)
            plt.show()


    def plotMaster(self):
        plt.figure(figsize=(30, 30))
        nx.draw(self.masterGraph, with_labels=True)
        plt.show()

    ####################################################################################################################
    ################################### Depreciated methods that might be reexamined ###################################
    ####################################################################################################################

    # def loadStatus(self, STATUS):
    #     """ A method that loads a one level dictionary of current volume/item states and applies it to the current graph"""
    #     for itemName, itemAttrs in self.edgesMaster.items():
    #         if 'volume' in itemAttrs:
    #             volAttrs = itemAttrs['volume']
    #             if itemName in STATUS:
    #                 curStatus = STATUS[itemName]
    #                 allStateInfo = volAttrs['STATES']
    #                 curStateInfo = list(filter(lambda x: x['STATE'] == curStatus, allStateInfo))[0]
    #                 commonNodes = curStateInfo['COMMON']
    #                 self.currentStates[itemName]['STATES'] = [{"STATE":curStatus, 'COMMON':[]}]
    #                 self.currentG.add_node(itemName)
    #                 for commonNode in commonNodes:
    #                     self.currentStates[itemName]['STATES'][0]['COMMON'].append(commonNode)
    #                     self.currentG.add_edge(itemName, commonNode)
    #             else:
    #                 self.currentStates[itemName]['STATES'] = []
    #                 for stateInfo in volAttrs['STATES']:
    #                     curStatus = {}
    #                     curStatus['STATE'] = stateInfo['STATE']
    #                     curStatus['COMMON'] = []
    #                     for commonNode in stateInfo['COMMON']:
    #                         addToCommon = True
    #                         if commonNode in STATUS.keys():
    #                             masterStatus = list(filter(lambda x: x['STATE'] == STATUS[commonNode], self.edgesMaster[commonNode].get('volume', {})['STATES']))
    #                             masterStatus = masterStatus[0]
    #                             common = masterStatus['COMMON']
    #                             if not itemName in common:
    #                                 addToCommon = False
    #                         if addToCommon:
    #                             curStatus['COMMON'].append(commonNode)
    #                             self.currentG.add_edge(itemName, commonNode, state=curStatus['STATE'])
    #
    #
    # def plotCurrent(self):
    #     plt.figure(figsize=(30, 30))
    #     nx.draw(self.currentG, with_labels=True)
    #     plt.show()
    #
    # def resetCurrent(self):
    #     for itemName, itemAttrs in self.edgesMaster.items():
    #         self.currentStates[itemName] = {'ITEM': itemName}
    #         self.currentStates['CURRENT_STATE'] = None
    #         pass

# todo: sync the component handlers with individual components
COMPONENT_HANDLERS = {
    'flow_valve': RoutingGraph._handleFlowValve,
    "directional": RoutingGraph._handleDirectionalValve,
    "shutoff": RoutingGraph._handleDirectionalValve,
    "pressure_regulator": RoutingGraph._handleFlowValve,
    "pressure_gauge": RoutingGraph._handleVolumeMeasurement,
    "pressure_transducer": RoutingGraph._handleVolumeMeasurement,
    "thermocouple": RoutingGraph._handleVolumeMeasurement,
    'flow_meter': RoutingGraph._handleFlowValve
}

def main():
    parser = RoutingGraph(CONTROLLER_ROUTING, EP_FILEPATH)
    # parser.plotMaster()
    # parser.shortestPath("GSH-1.VOL-1", "1W-11")
    # parser.shortestPath('GSH-3.VOL-1', '4W-11')
    parser.shortestPath("GSH-4.VOL-1", '7P4-22')
    # todo: validate this with a few paths from each gas house/pad


if __name__ == '__main__':
    main()