import threading

from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Events import EventPayload, EventTypes
from Framework.BaseClasses.Package import Package

"""Resources will be resourceKeyed off of a main resourceKey, and sub resourceKey per resource. """
# todo: do some unit testing on this class!
#  integrate this into things like the GUI, controller box stuff with commands

class ResourceLock():
    def __init__(self, resourceKey, subKey=None):
        self.resourceKey = resourceKey
        self.subKey = subKey
        self.holder = None
        self.held = False

    def isHeld(self):
        return self.held

    def obtain(self, holder):
        if not self.isHeld:
            self.holder = holder
            self.held = True
        else:
            raise Exception(f'Lock cannot be granted to object {holder} as it is already held by object {holder}')

    def release(self, holder, override = False):
        if holder is self.holder or override:
            self.holder = None
            self.held = True
        else:
            raise Exception(f'Lock cannot be released by object that does not hold the lock unless override is set to True.')


RESOURCES = {
    "exampleKey":{
        "resourceLock": ResourceLock("exampleKey"),
        "subKeys":{}
    }
}

class ResourceAllocator():
    def __init__(self):
        self.RA_Lock = threading.RLock()

    def _addSingleResource(self, resourceName):
        RESOURCES[resourceName] = {'resourceLock': ResourceLock(resourceName),
                                   'subKeys':{}}

    def addResource(self, resourceName, subkeys=None, overwrite=False):
        subkeys = subkeys if subkeys else {}
        with self.RA_Lock:
            if not resourceName in RESOURCES:
                self._addSingleResource(resourceName)
            elif overwrite:
                pass
            else: # resource name exists and overwrite is set to false.
                raise Exception(f'A resource with the name {resourceName} already exists, and overwrite is set to False.')
            self.addSubkeys(resourceName, subkeys)

    def addSubkeys(self, resourceName, subKeys, overwrite=False):
        with self.RA_Lock:
            if not resourceName in RESOURCES:
                self._addSingleResource(resourceName)
            thisResource = RESOURCES[resourceName]
            for singleKey in subKeys.keys():
                if singleKey in thisResource:
                    if overwrite:
                        del thisResource[singleKey]
                    else:
                        raise Exception(f'A resource subKey with the name {singleKey} already exists for resource {resourceName}')
                thisResource[singleKey] = ResourceLock(resourceName, subKey=singleKey)

    def removeResource(self, resourceName):
        raise NotImplementedError

    def obtainLock(self, requestor, resourceKey, subKey): # # obtaining lock for mater lock should obtain it for subkeys
        with self.RA_Lock:
            lock = self.accessLock(resourceKey, subKey)
            lock.obtain(requestor)
            pl = EventPayload(source=resourceKey, eventType=EventTypes.LockWidget, requestor=requestor, state=True)
            pkg = Package(source="ResourceAllocator", payload=pl, channelType=ChannelType.Event)
            # eventmanager.emit(pkg)
            return lock

    def releaseLock(self, requestor, resourceKey, subKey):
        with self.RA_Lock:
            lock = self.accessLock(resourceKey, subKey)
            lock.release(requestor)
            return lock

    def accessLock(self, resourceKey, subKey=None):
        with self.RA_Lock:
            if resourceKey in RESOURCES:
                if subKey:
                    if subKey in RESOURCES[resourceKey]['subKeys']:
                        lock = RESOURCES[resourceKey]['subKeys']
                        return lock
                else:
                    lock = RESOURCES[resourceKey]['resourceLock']
                    return lock
            raise Exception(f'Unable to access lock for resource {resourceKey} and subkey {None}; Lock does not exist.')