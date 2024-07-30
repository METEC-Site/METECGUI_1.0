import threading


class RepeaterThread(threading.Thread):
    """ A thread that runs a method on a timer every [interval] seconds. """
    def __init__(self, stopper, logger, name, target, interval, *args, **kwargs):
        self.logger = logger
        self.__args = args
        self.__kwargs = kwargs
        threading.Thread.__init__(self, name=name)
        self.__method = target
        self.__stopper = stopper
        self.__interval = interval

    def run(self):
        self.logger.debug(f'Starting {self.name} repeater thread method {self.__method}')
        while not self.__stopper.wait(self.__interval):
            try:
                self.__method(*self.__args, **self.__kwargs)
            except Exception as e:
                self.logger.debug(f'Attempted to run repeated method {self.__method} but was unable to due to exception: {e}')