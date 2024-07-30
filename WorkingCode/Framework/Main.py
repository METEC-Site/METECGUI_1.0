import importlib.util
import json
import logging
import os
import sys
import time

# Adding command framework to the path, as this framework assumes that is set as a project root.
# Many imports are relative to that.
cmdFrameworkPath = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(cmdFrameworkPath)

from Framework.BaseClasses.Factory import Factory
from Framework.Manager.ObjectManager import ObjectManager
from Utils import ClassUtils as cu
from Utils import FileUtils as fUtils

# This is the format of the expected commandline argument. One and only one is needed, and that is the path to the config
# file that will generate the instance of the Framework.
ARGS_METADATA = {
    'description': 'Main',
    'args': [
        {'name_or_flags': ['-c', '--configFile'],
         'default': None,
         'help': 'Configuration file used by the main as a factory to create the program.  (default: %(default)s)'}
    ]
}

def loadConfigDict():
    args = fUtils.getArgs(ARGS_METADATA)
    configPath = args.configFile
    if not configPath:
        raise TypeError("You must specify a config file with either -c or --configFile")

    modDir, modDotExt = os.path.split(configPath)
    modName, ext = os.path.splitext(modDotExt)
    configDict = None
    if ext == '.py':
        # spec = PathFinder.find_spec(modName, configPath)
        # module = module_from_spec(spec)
        # spec.loader.exec_module(module)
        # configDict = module.configDict
        spec = importlib.util.spec_from_file_location(modName, configPath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        configDict = module.configDict
    elif ext == '.json':
        with open(configPath) as cFile:
            configDict = json.load(cFile)
    return configDict

def makeArchiver(configDict):
    archFact = Factory(configDict['Archiver'])
    da = archFact.make()
    return da

def makeManagers(archiver, configDict):
    cmFact = Factory(configDict['CommandManager'])
    dmFact = Factory(configDict['DataManager'])
    emFact = Factory(configDict['EventManager'])
    cm = cmFact.make(archiver)
    dm = dmFact.make(archiver)
    em = emFact.make(archiver)
    cm.setEventManager(em)
    cm.setDataManager(dm)
    dm.setCommandManager(cm)
    dm.setEventManager(em)
    em.setCommandManager(cm)
    em.setDataManager(dm)
    return cm, dm, em

def makeWorkers(archiver, commandManager, dataManager, eventManager, configDict):
    wkrs = []
    for workerConfig in configDict['Workers']:
        workerFact = Factory(config=workerConfig)
        wkr = workerFact.make(archiver, commandManager, dataManager, eventManager)
        if type(wkr) is list:
            for singleWkr in wkr:
                wkrs.append(singleWkr)
        else:
            wkrs.append(wkr)
    return wkrs

def startAllObjects(objs):
    for singleObj in objs:
        singleObj.start()

def startInit(configDict):
    initConfig = configDict.get('Init')
    if initConfig:
        initFact = Factory(config=initConfig)
        init = initFact.make()
        init.start()
    else:
        pass

def systemShutdown():
    allRegisteredObjects = ObjectManager.getRegistry()
    archiver = list(filter(lambda x: cu.isArchiver(x), allRegisteredObjects.values()))
    cm = list(filter(lambda x: cu.isCommandManager(x), allRegisteredObjects.values()))
    dm = list(filter(lambda x: cu.isDataManager(x), allRegisteredObjects.values()))
    em = list(filter(lambda x: cu.isEventManager(x), allRegisteredObjects.values()))
    mgrs = [*cm, *dm, *em]
    otherObjs = list(filter(lambda x: x not in [archiver, cm, dm, em], allRegisteredObjects.values()))
    for obj in otherObjs:
        try:
            obj.end()
        except Exception as e:
            logging.exception(f'Could not shut down object properly.'
                          f'\n\tobj: {obj.getName()}'
                          f'\n\terror: {e}')
    for mgr in mgrs:
        try:
            mgr.end()
        except Exception as e:
            logging.exception(f'Could not shut down object properly.'
                          f'\n\tobj: {mgr.getName()}'
                          f'\n\terror: {e}')
    for ar in archiver:
        try:
            ar.end()
        except Exception as e:
            logging.exception(f'Could not shut down object properly.'
                          f'\n\tobj: {ar.getName()}'
                          f'\n\terror: {e}')

def mainLoop():
    logging.info(f'Entering main loop.')
    stopper = ObjectManager.getStopper()
    while not stopper.is_set():
        time.sleep(0.01)
        pass
    logging.info('Shutting Down Main Program')
    try:
        systemShutdown()
    finally:
        time.sleep(2)
        # sys.exit(0)
        os._exit(0)


def main():
    # load in a dictionary of the config file
    configDict = loadConfigDict()

    # Order of object instantiation: Archiver, [Managers], Workers, and then final init method (init is optional)
    # Factory takes a dictionary with module and class keys, and any number of extra keys. This factory passes in all
    # keys/values as kwargs to the module/class instance.
    # To make the object, call 'make' on that factory, passing in any final args or kwargs in the make method which will
    # be passed to the module/class instance.
    da = makeArchiver(configDict)
    with da:
        cm, dm, em = makeManagers(da, configDict)
        wkrs = makeWorkers(da, cm, dm, em, configDict)

        # Order of starting is Archiver, [managers], workers, init (init is optional). This order is the same as the
        # order of instantiation.
        allObjs = [da, cm, dm, em, *wkrs]
        startAllObjects(allObjs)

        # Call init method if there is one. Otherwise, log that the system started successfully.
        logging.info('System Started')
        startInit(configDict) # todo: fix where closing the main window of a gui and sending a shutdown signal doesn't close the main app.

        # This next loop will run forever, until the system shutdown method is run or a keyboard interrupt occurs.
        # Options for shutting down the process:
            # 1) Raise a shutdown event and pass it to the event manager. It will call the systemShutdown method with the
            #       process namespace.
            # 2) Execute a keyboard interrupt from the command line.
        # Both these options do the same thing: call end on all registered objects, end the destination threads of all
        # destinations, and give time for the threads to finish (2 seconds) before finally exiting from the program.
        mainLoop()


if __name__ == '__main__':
    main()