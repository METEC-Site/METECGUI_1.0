"""
###################
Archiver Base Class
###################

:Authors: Aidan Duggan, Jerry Duggan
:Date: April 20, 2019

.. _archiver-base-module:

A base class for subclasses to inherit abstract methods from.

"""
__docformat__ = 'reStructuredText'

from abc import ABC, abstractmethod

import Utils.TimeUtils as tu
# from Framework.BaseClasses.FrameworkObject import FOMetaclass, FrameworkObject # commented out to transition to Frameworkv2
from Framework.BaseClasses.Registration.FrameworkRegistration import FrameworkObject


class Archiver(FrameworkObject, ABC):
    """This class is intended to act as a base class for inherited subclasses.

    .. _archiver-base-class:

    When a subclass inherits from Archiver, it **must** implement the following abstract methods:

        * getName
        * getChannels
        * getMetadata
        * createChannel
        * read
        * getFLO

    .. note::
        The :ref:`isArchiver <is-archiver>` method checks to see if this class appears as any of the subclass's bases.
    """
    def __init__(self, name, **kwargs):
        super().__init__(name=name, **kwargs)
        # FrameworkObject.__init__(self, name=name, **kwargs)

    @abstractmethod
    def getChannels(self):
        pass

    @abstractmethod
    def createChannel(self, name, channelType, metadata=None, path=None):
        pass

    @abstractmethod
    def getMetadata(self, channel):
        pass

    @abstractmethod
    def read(self, channel, minTS=tu.MIN_EPOCH, maxTS=tu.MAX_EPOCH, interval='1s'):
        pass