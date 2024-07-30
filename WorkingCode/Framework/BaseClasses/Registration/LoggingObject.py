import logging

from Framework.BaseClasses.NamedObject import NamedObject


class LoggingObject(NamedObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(self.getName())