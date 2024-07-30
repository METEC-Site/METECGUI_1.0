from Framework.BaseClasses.Destination import ThreadedDestination
from Framework.BaseClasses.Worker import Worker
from Utils import ClassUtils as cu


class Subscriber(Worker, ThreadedDestination):
    def __init__(self, name=None, archiver=None, commandManager=None, dataManager=None, eventManager=None,
                 commandSubscriptions=None, dataSubscriptions=None, eventSubscriptions=None, **kwargs):
        super().__init__(archiver=archiver, commandManager=commandManager, dataManager=dataManager, eventManager=eventManager, name=name, **kwargs)
        # ThreadedDestination.__init__(self, name=name)
        # Worker.__init__(self, archiver=archiver, commandManager=commandManager, dataManager=dataManager, eventManager=eventManager, name=name)
        self.commandSubscriptions = commandSubscriptions
        self.dataSubscriptions = dataSubscriptions
        self.eventSubscriptions = eventSubscriptions
        if self.commandSubscriptions is None:
            self.commandSubscriptions = []
        if self.dataSubscriptions is None:
            self.dataSubscriptions = []
        if self.eventSubscriptions is None:
            self.eventSubscriptions = []
        if cu.isCommandManager(commandManager):
            for singleCMDSub in self.commandSubscriptions:
                commandManager.subscribe(self, **singleCMDSub)
        if cu.isDataManager(dataManager):
            if len(self.dataSubscriptions) == 0:
                dataManager.subscribe(self)
            else:
                for singleDATASub in self.dataSubscriptions:
                    dataManager.subscribe(self, **singleDATASub)
        if cu.isEventManager(eventManager):
            if len(self.eventSubscriptions) == 0:
                eventManager.subscribe(self)
            else:
                for singleEVENTSub in self.eventSubscriptions:
                    eventManager.subscribe(self, **singleEVENTSub)
