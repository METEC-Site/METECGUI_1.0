from abc import ABC

from Framework.BaseClasses.Destination import ThreadedDestination
# from Framework.BaseClasses.FrameworkObject import FOMetaclass, FrameworkObject # commented out to transition to Frameworkv2
from Framework.BaseClasses.Registration.FrameworkRegistration import FrameworkObject
from Utils import ClassUtils as cu

"""
.. _worker-base-class:

#################
Worker Base Class
#################

:Authors: Aidan Duggan, Jerry Duggan
:Date: April 23, 2019

This module provides the Base Worker Class
"""
__docformat__ = 'reStructuredText'

class Worker(FrameworkObject, ThreadedDestination, ABC):
    # L[W] = [W, ABC]
    """ This class is the base for any inherited worker object.

    .. _worker-base-class:

    The purpose of this class is to provide a unified base for all 'worker' objects. All workers must be passed an
    archiver, commandManager, dataManager, eventManager, and name object. The name must be unique amongst all workers,
    and the archiver and managers can either be None, or must inherit from the corresponding base class

    :param archiver:
    :type archiver: Archiver or None
    :param commandManager:
    :type commandManager: CommandManager or None
    :param dataManager:
    :type dataManager: DataManager or None
    :param eventManager:
    :type eventManager: EventManager or None
    :param name:
    :type name: str
    :raises TypeError: Passed objects are not None and don't inherit from the correct base class, or name is not unique.


    .. note::
        This base class is what :ref:`ClassUtils.isWorker  <cu-is-worker>` searches for when examining an object's base classes.

    .. seealso::
        :ref:`isWorker <cu-is-worker>`

    """

    def __init__(self, archiver=None, commandManager=None, dataManager=None, eventManager=None, name=None, **kwargs):
        super().__init__(archiver=archiver, commandManager=commandManager, eventManager=eventManager, name=name, **kwargs)
        # FrameworkObject.__init__(self, **kwargs)
        # ThreadedDestination.__init__(self, **kwargs)
        error = ''
        if not cu.isArchiver(archiver) and not archiver is None:
            error += f'ERROR: Object passed as archiver is neither an Archiver nor None.\n'
        if not cu.isCommandManager(commandManager) and not commandManager is None:
            error += f'ERROR: Object passed as commandManager is neither a CommandManager nor None.\n'
        if not cu.isDataManager(dataManager) and not dataManager is None:
            error += f'ERROR: Object passed as dataManager is neither a DataManager nor None.\n'
        if not cu.isEventManager(eventManager) and not eventManager is None:
            error += f'ERROR: Object passed as eventManager is neither an EventManager nor None.\n'
        if not error == '':
            raise TypeError(error)
        self.archiver=archiver
        self.commandManager = commandManager
        self.dataManager = dataManager
        self.eventManager = eventManager

    # todo: is the worker class the best place for this (these) methods?
    def setEventManager(self, eventManager):
        if cu.isEventManager(eventManager):
            self.eventManager = eventManager
            return True
        else:
            return False

    def setCommandManager(self, commandManager):
        if cu.isCommandManager(commandManager):
            self.commandManager = commandManager
            return True
        else:
            return False

    def setDataManager(self, dataManager):
        if cu.isDataManager(dataManager):
            self.dataManager = dataManager
            return True
        else:
            return False