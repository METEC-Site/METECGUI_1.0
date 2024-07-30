from Applications.METECControl.TestSuite.Base import Operation as ops
from Utils import FileUtils as fUtils


READER_CONFIG_PATH = "C:\\Users\\AADug\\Documents\\CommandFramework\\CommandFramework\\Applications\\METECControl\\Config\\NewSiteMetadata\\readers.json"
READER_CONFIG = fUtils.loadJson(READER_CONFIG_PATH)
DEVICE_CONFIG_PATH = 'C:\\Users\\AADug\\Documents\\CommandFramework\\DevBranch\\Applications\\METECControl\\Config\\SiteMetadata\\SiteConfig-Feb_2020.csv'
DEVICE_CONFIG = fUtils.loadCSV(DEVICE_CONFIG_PATH)
EP_CONFIG_PATH = "C:\\Users\\AADug\\Documents\\Monitor\\Operations\\ConfigurationAndCalibrationRecords\\EmissionPointConfigurations\\EmissionPointConfig20191118130040.xlsx"
EP_CONFIG = fUtils.loadXLSX(EP_CONFIG_PATH)
FM_CONFIG_PATH = "C:\\Users\\AADug\\Documents\\Monitor\\Operations\\ConfigurationAndCalibrationRecords\\FlowMeterConfigurations\\FlowMeterConfig-OGIPracticalClass.xlsx"
FM_CONFIG = fUtils.loadXLSX(FM_CONFIG_PATH)


def main():
    ep1Name = 'EP1'
    singleRelease = ops.SinglePointEmission(7, 5, ep1Name, stopOnExit=False)
    intermittent = ops.IntermittentEmission(ep1Name, 4, 2, 10, 2)
    singleRelease.interpret()
    intermittent.interpret()

if __name__ == '__main__':
    main()