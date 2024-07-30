import logging

import Utils.FileUtils as fUtils


class CreationException(Exception):
    pass

def makeInterface(**kwargs):
    try:
        module = kwargs.pop('module')
        cls = kwargs.pop('class')
        clsDef = fUtils.loadClass(module, cls)
        clsInst = clsDef(**kwargs)
        return clsInst
    except Exception as e:
        logging.exception(f'Could not create a listener instance due to error {e}')
    raise CreationException