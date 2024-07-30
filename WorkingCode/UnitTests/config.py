import os

cfg1Base = os.path.abspath(os.path.join(os.path.dirname(__file__), '../UnitTests/TestArchiver'))

configDict = {
    'Namespace': 'UnitTesting',
    'Archiver': {
        'module': 'Framework.Archive.DirectoryArchiver',
        'class': 'DirectoryArchiver',
        'name': 'Archiver',
        'readOnly': False,
        'restart': False,
        'template': '%Y-%m-%d_%H-%M-%S',
        'rolloverCriteria': 'time',
        'rolloverInterval': 86399,
        'checkROInterval' : 10,
        'baseDir': './TestData/ReadOnly'
    },
    "CommandManager":{
        'module': 'Framework.Manager.CommandManager',
        'class': 'CommandManager',
        'name': 'CMD_MGR'
    },
    "EventManager":{
        'module': 'Framework.Manager.EventManager',
        'class': 'EventManager',
        'name': 'EVNT_MGR'
    },
    "DataManager": {
        'module': 'Framework.Manager.DataManager',
        'class': 'DataManager',
        'name': 'DATA_MGR'
    },
    'Workers': [
        {
            'module': 'UnitTests.TestMain',
            'class': 'MainEnder',
            'name': 'ender',
            'stopSecs': 2
        }
    ]
}