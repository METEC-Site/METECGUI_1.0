import Utils.FileUtils as fUtils

class Factory:
    def __init__(self, config={}, module=None, cls=None, **kwargs):
        module = config.get('module') if not module else module
        cls = config.get('class') if not cls else cls
        self.configDict = config
        self.cls = fUtils.loadClass(module, cls)

    def make(self, *args, **kwargs):
        # Any kw that is in configDict will be overwritten by passed kwargs if both exist and have the same key name.
        passedkws = {**self.configDict, **kwargs}
        return self.cls(*args, **passedkws)