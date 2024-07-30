import os
import sys

# cmdFrameworkPath = 'D:\\SVNs\\METEC_SVN\\Facility Operations\\ConfigurationAndCalibrationRecords'
# sys.path.append(cmdFrameworkPath)


cfg1Base = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Config'))
cfg2Base = "D:\\SVNs\\METEC_SVN\\Facility Operations\\ConfigurationAndCalibrationRecords\\EmissionPointConfigurations"
gcbase = "D:\\SVNs\\METEC_SVN\\Facility Operations\\ConfigurationAndCalibrationRecords\\GasCompositions"

configDict = {
    "Namespace": "METEC Secondary GUI",
    'Archiver': {
        'module': 'Framework.Archive.DirectoryArchiver',
        'class': 'DirectoryArchiver',
        'name': 'Archiver',
        'readonly': False,
        'restart': False,
        'template': '%Y-%m-%d_%H-%M-%S',
        'rolloverCriteria': 'time',
		'utcStartHMS': '0:00:00',
        'rolloverInterval': 86400,
        'checkROInterval' : 10,
        'baseDir': 'D:\\SiteData\\GUI',
        'configFiles': [
            {'channel': 'Logging',               'basePath': cfg1Base,                              'fileName': "Logging.json"},
            {'channel': 'metDisplayConfig-user', 'basePath': cfg1Base, 'subPath': 'GUI',            'fileName': 'metDisplayConfig-user.json'}
        ],
        "manifests": []
    },
    'CommandManager':{
        'module': 'Framework.Manager.CommandManager',
        'class': 'CommandManager',
        'name': 'CMD_MGR'
    },
    'EventManager':{
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
            'module': 'Applications.METECControl.Factories.LabJackFactory',
            'class': 'LabJackFactory',
            'fakeServer': False,
            "readerSummary": "D:\\SVNs\\METEC_SVN\\Facility Operations\\ConfigurationAndCalibrationRecords\\ReaderRecords\\ReaderSummary.csv"
        },
        # {
        #     'module': 'Applications.METECControl.Factories.AlicatFactory',
        #     'class': 'AlicatFactory',
        #     "readerSummary": "C:\\Users\\METEC\\Documents\\SVN_METEC\\Operations\\ConfigurationAndCalibrationRecords\\ReaderRecords\\ReaderSummary.csv"
        # },
        {
            'module': 'Applications.METECControl.GUI.GUIInterface',
            'class': 'GUIInterface',
            'blocking': True,
            'qtimeout': None,
            "readerSummaryFile": "D:\\SVNs\\METEC_SVN\\Facility Operations\\ConfigurationAndCalibrationRecords\\ReaderRecords\\ReaderSummary.csv",
            "fmSummaryFile": "D:\\SVNs\\METEC_SVN\\Facility Operations\\ConfigurationAndCalibrationRecords\\FlowMeterConfigurations\\FMConfigSummary.csv",
            "epSummaryFile": "D:\\SVNs\\METEC_SVN\\Facility Operations\\ConfigurationAndCalibrationRecords\\EmissionPointConfigurations\\EPConfigSummary.csv",
            "gcSummaryFile": "D:\\SVNs\\METEC_SVN\\Facility Operations\\ConfigurationAndCalibrationRecords\\GasCompositions\\GCRecords\\GasCompositionSummary.csv"
        },
        {
            'module': 'Applications.METECControl.Readers.CorrectionFactor',
            'class': 'CorrectionFactor',
            'blocking': True,
            'qtimeout': None,
            "readerSummary": "D:\\SVNs\\METEC_SVN\\Facility Operations\\ConfigurationAndCalibrationRecords\\ReaderRecords\\ReaderSummary.csv",
            'gcSummary': "D:\\SVNs\\METEC_SVN\\Facility Operations\\ConfigurationAndCalibrationRecords\\GasCompositions\\GCRecords\\GasCompositionSummary.csv"
        }
    ],
    "Init": {
        'module': 'Utils.QtUtils',
        'class': 'StartApp'
    }
}

def main():
    from Framework import Main
    import sys
    sys.argv = [__file__,
        '--configFile',
        __file__]
    Main.main()


if __name__ == '__main__':
    main()