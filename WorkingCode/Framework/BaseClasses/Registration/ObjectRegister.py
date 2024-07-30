from threading import RLock

from Utils import ClassUtils as cu
from Utils import Exceptions as ex


class Registry:
    RegistryLock = RLock()
    OBJECT_REGISTRY = {}
    """ A registry is a wrapper around a global registry, were one ane only one object can register with a unique name.
    This class is designed as an accessor/manager around such as registry."""

    ####################################################################################################################
    ####################################### Methods for getting/setting objects ########################################
    ####################################################################################################################
    @classmethod
    def getAllObjects(cls):
        objs = list(cls.OBJECT_REGISTRY.values())
        return objs

    @classmethod
    def getAllNames(cls):
        names = list(cls.OBJECT_REGISTRY.keys())
        return names

    @classmethod
    def getObject(cls, objName):
        with cls.RegistryLock:
            if cls.nameInRegistry(objName):
                return cls.OBJECT_REGISTRY[objName]
            return None

    ####################################################################################################################
    ################################## Methods for registering/unregistering objects ###################################
    ####################################################################################################################

    @classmethod
    def registerObject(cls, obj, asObjName=None):
        """ Register an object (must be a FrameworkObject) within the global registry.

        This method will register an object to the registry. Two objects may never be registered under the same name,
        but one instance of an object can be registered under any number of names.

        :param obj: an object to be registered within the registry
        :type obj: FrameworkObject
        :param asObjName: The channelName under which the object will be registered. If not supplied, then use the obj.channelName attribute.
        :type asObjName: str
        :return: True if successful and the object was registered (or if the object already existed within the registry)
            or False if the object was unable to be added to the registry."""
        with cls.RegistryLock:
            if not cu.isFrameworkObject(obj):
                raise ex.InheritError(f'Object {obj} does not inherit from FrameworkObject and cannot be added to the Object Manager.')
            asObjName = asObjName if asObjName else obj.getName()

            if cls.objectInRegistry(obj):# Object already registered.
                return True
            if cls.nameInRegistry(asObjName): # something else already exists with that name.
                raise ex.NameConflict(f'Object with name {asObjName} already exists in registry, cannot add new instance.')
            cls.OBJECT_REGISTRY[asObjName] = obj # todo: check if this is correct?
            return True

    @classmethod
    def unregisterObject(cls, obj):
        with cls.RegistryLock:
            if not cu.isFrameworkObject(obj):
                raise ex.InheritError(f'Object {obj} does not inherit from FrameworkObject, cannot unregister from ObjectManager.')
            objName = obj.getName()
            if cls.nameInRegistry(objName):
                cls.OBJECT_REGISTRY.pop(objName)
            return True

    ####################################################################################################################
    ################################ Methods for getting/checking references to objects ################################
    ####################################################################################################################

    @classmethod
    def objectInRegistry(cls, obj):
        with cls.RegistryLock:
            if obj in cls.getAllObjects():
                return True
            return False

    @classmethod
    def nameInRegistry(cls, name):
        with cls.RegistryLock:
            if name in cls.getAllNames():
                return True
            return False

    @classmethod
    def getRegisteredNames(cls, obj):
        """returns a list of all names that an object is registered under."""
        with cls.RegistryLock:
            registeredNames = list(filter(lambda x: cls.OBJECT_REGISTRY['Objects'][x] is obj, cls.OBJECT_REGISTRY['Objects'].keys()))
            return registeredNames

    ####################################################################################################################
    ################################## Method getting direct access to the registry. ###################################
    ####################################################################################################################

    @classmethod
    def getRegistry(cls):
        return cls.OBJECT_REGISTRY

    @classmethod
    def endRegistry(cls):
        with cls.RegistryLock:
            for obj in cls.getAllObjects():
                cls.unregisterObject(obj)