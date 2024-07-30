"""
.. _tee_pipe_module:

########
Tee Pipe
########

:Authors: Aidan Duggan, Jerry Duggan
:Date: April 26, 2019

A module that provides a non-threaded pipe with multiple destinations.
"""
from Framework.BaseClasses.Destination import Destination
from Utils import ClassUtils as cu

class TeePipe(Destination):
    """ A class that accepts data from one end, and passes it to all its destinations accept methods.

    When an object needs to send data to another and the destination object is a :ref:`Destination <dest-class>`,
    it will pass it to that object's :py:func:accept method.
    """

    def __init__(self, name=None, destinations=[], **kwargs):
        Destination.__init__(self, name)
        if not type(destinations) is list:
            destinations = [destinations]

        for singleDest in destinations:
            if not cu.isDestination(singleDest):
                raise TypeError(f'\'destination\' argument for TeePipe named {name} expects a Destination object or list'
                                f' of Destination objects.')
        self.destinations = destinations
        self.terminate = False

    def addDestination(self, destination):
        if not cu.isDestination(destination):
            raise TypeError(f'Can only add an object of Type to Tee Pipe named {self.name}')
        self.destinations.append(destination)

    def handlePackage(self, package):
        for destination in self.destinations:
            destination.accept(package)