import logging

from Framework.BaseClasses.FrameworkObject import FrameworkObject


class TestLogEmitter(FrameworkObject):
    def emitLog(self):
        msg = f'Debug message from {self.name}'
        self.logger.debug(f'{self.logger.name} | {msg}')
        logging.debug(f'Root | {msg}')
        return msg

    def end(self):
        pass

    def start(self):
        pass

    def _onExitCleanup(self):
        FrameworkObject._onExitCleanup(self)