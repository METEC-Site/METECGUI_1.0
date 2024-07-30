import logging

from Framework.BaseClasses.Destination import Destination
from Utils import ClassUtils as cu


class ThreadedPipe(Destination):
    """
    A pipe operating in its own thread. Like a thread, it has a run method that must be executed by the start() method
    after instantiation. It also must have at least one destination before being run.

    An outside operation puts something in the threaded pipe by calling its "accept" method. Then, the thread will run
    through its own internal queue and, for each destination, will call the destination's accept method. The queue will
    block until there is something in it, though if qtimeout is specified then the queue will timeout after that many
    seconds. This will continue to occur until the pipe's terminate is set to True.
    """
    def __init__(self, destinations, name=None, blocking=True, qtimeout=None, *args, **kwargs):
        """

        Parameters
        ----------
        destinations : Destination or list of Destinations
            Custom class destination. Must have an 'accept' method.
        blocking : bool
            Specifies if the queue will block. Defaults to blocking (True) behavior.
        qtimeout : int
            Specifies the max amount of secs the queue will block for before timing out. Defaults to None, or no timeout.
        """
        Destination.__init__(self, name=name)
        self.destinations = destinations if type(destinations) is list else [destinations]
        self.qtimeout = qtimeout
        self.blocking = blocking

    def addDestination(self, destination):
        """ Function that adds a destination to the internal list of destinations"""
        if not cu.isFrameworkObject(destination):
            raise TypeError(f'Cannot add destination {destination} to Pipe {self.name}; Destination is not a FrameworkObject. ')
        if not destination in self.destinations:
            self.destinations.append(destination)
            return True
        logging.debug('Attempted to add duplicate destination {} to threaded pipe {}'.format(destination, self.name))

    def handlePackage(self, package):
        for destination in self.destinations:
            destination.accept(package)