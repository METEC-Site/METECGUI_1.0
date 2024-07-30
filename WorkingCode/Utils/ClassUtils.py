"""
.. _class-utils-module:

###########
Class Utils
###########


A module that provides a util to check all of a class's bases for a specific base.

:Authors: Aidan Duggan, Jerry Duggan
:Date: April 23, 2019


"""

__docformat__ = 'reStructuredText'

import Framework.BaseClasses.Package


def isClass(obj, cls):
    """ A method that checks the object to see if it is or inherits from a specific class

    .. _cu-is-class:



    :param obj: A class definition or instance of a class.
    :param cls: A class definition
    :return: Bool: True if the obj matches/inherits the class, False if not.


    .. note::
        This method checks all the inherited super classes, not just the one immediately inherited from.


    .. seealso::
        :ref:`ClassUtils.allBases <cu-all-bases>`
    """
    try:
        if cls in allBases(obj) or obj is cls or type(obj) is cls:
            return True
    except AttributeError:
        if cls in allBases(type(obj)) or type(obj) is cls:
            return True
    return False


def allBases(cls):
    """ A method that returns all classes within an object/class definition's inheritance tree.

    .. _cu-all-bases:

    :param cls:
    :return: list of all classes in inheritance tree.
    """
    try:
        clses = [base for base in cls.__bases__]
        for baseCls in clses:
            clses.extend(allBases(baseCls))
    except AttributeError as e:
        return list(set([type(cls), *allBases(type(cls))]))
    except NameError as e:
        return list(set([type(cls), *allBases(type(cls))]))
    except TypeError as e:
        return list(set([type(cls), *allBases(type(cls))]))
    return list(set(clses))


def isWorker(obj):
    """ A class that checks if an object is or inherits from the Worker Base Class

    .. _cu-is-worker:

    :param obj: An object for which the type/inheritance needs to be checked.
    :return: Bool, True if obj inherits from Worker, False otherwise.

    .. seealso::
        :ref:`Worker Base Class <worker-base-class>`
        :ref:`ClassUtils.isClass <cu-is-class>`
    """
    import Framework.BaseClasses.Worker as wkr
    return isClass(obj, wkr.Worker)


def isReadPipe(obj):
    import Framework.Pipes.ReadPipe as rp
    return isClass(obj, rp.ReadPipe)


def isFrameworkObject(obj):
    # from Framework.BaseClasses.FrameworkObject import FOMetaclass, FrameworkObject # commented out to transition to Frameworkv2
    import Framework.BaseClasses.Registration.FrameworkRegistration as fr
    return isClass(obj, fr.FrameworkObject)


def isDestination(obj):
    import Framework.BaseClasses.Destination as dest
    return isClass(obj, dest.Destination)


def isReader(obj):
    import Framework.BaseClasses.Readers.Reader as rdr
    return isClass(obj, rdr.Reader)


def isSubscriber(obj):
    import Framework.BaseClasses.Subscriber as sub
    return isClass(obj, sub.Subscriber)

def isSentinel(obj):
    import Framework.BaseClasses.Sentinel as pkg
    return isClass(obj, Framework.BaseClasses.Package.Sentinel)

def isPackage(obj):
    import Framework.BaseClasses.Package as pkg
    return isClass(obj, pkg.Package)


def isPayload(obj):
    import Framework.BaseClasses.Package as pkg
    return isClass(obj, pkg.Payload)


def isEvent(obj):
    import Framework.BaseClasses.Events as ev
    return isClass(obj, ev.EventPayload)


def isCommand(obj):
    import Framework.BaseClasses.Commands as cmd
    return isClass(obj, cmd.CommandPayload)


def isCommandClass(obj):
    import Framework.BaseClasses.Commands as cmd
    return isClass(obj, cmd.CommandClass)


def isChannelIO(obj):
    import Framework.Archive.ChannelIO
    return isClass(obj, Framework.Archive.ChannelIO.ChannelIO)


def isReaderClass(obj):
    import Framework.BaseClasses.Readers.Reader as rdr
    return isClass(obj, rdr.Reader)


def isCommandManager(obj):
    import Framework.BaseClasses.Manager as mgr
    return isClass(obj, mgr.CommandManager_Base)

def isManifestManager(obj):
    import Framework.BaseClasses.ManifestManager as mgr
    return isClass(obj, mgr.ManifestManager)

def isProxy(obj):
    import Framework.BaseClasses.Manager as mgr
    return isClass(obj, mgr.Proxy_Base)


def isEventManager(obj):
    import Framework.BaseClasses.Manager as mgr
    return isClass(obj, mgr.EventManager_Base)


def isDataManager(obj):
    import Framework.BaseClasses.Manager as mgr
    return isClass(obj, mgr.DataManager_Base)


def isRolloverManager(obj):
    import Framework.Archive.RolloverManager as ro
    return isClass(obj, ro.RolloverManager)


def isArchiver(obj):
    """A method to check if an object is or inherits from the :ref:`Archiver Base Class <archiver-base-class>`

    .. _is-archiver:

    :param obj: Class definition or instance to check.
    :type obj: class definition or object.
    :return: Bool. True if inherits from or is Archiver Base Class, or False if not.

    .. seealso:
        :ref:`Archiver Base Class <archiver-base-class>`
    """
    import Framework.BaseClasses.Archiver as ar
    return isClass(obj, ar.Archiver)

def isMetadata(obj):
    import Framework.BaseClasses.Metadata as md
    return isClass(obj, md.Metadata)

def isFormatter(obj):
    import Framework.Archive.Formatters
    return isClass(obj, Framework.Archive.Formatters.Formatter)


def isTestCase(obj):
    import unittest
    return isClass(obj, unittest.TestCase)



