import importlib.util
import os
import unittest

from Utils import ClassUtils as cu


def main():
    unitTestDir = os.path.dirname(__file__)
    testCases = []
    for base, subDirs, files in os.walk(unitTestDir):
        for file in files:
            if not 'pyc' in file and 'py' in file:
                wholePath = os.path.abspath(os.path.join(base, file))
                if os.path.isfile(wholePath):
                    module = importModuleFromFile(wholePath)
                    for name, thing in module.__dict__.items():
                        if cu.isTestCase(thing):
                            testCases.append(thing)
    loader = unittest.TestLoader()
    suites = []
    for testClass in testCases:
        suite = loader.loadTestsFromTestCase(testClass)
        suites.append(suite)
    allTests = unittest.TestSuite(suites)
    runner = unittest.TextTestRunner()
    results = runner.run(allTests)


def importModuleFromFile(filePath):
    head, filename = os.path.split(filePath)
    modName = filename.split('.')[0]
    # modName = 'CommandFramework.UnitTests.' + modName
    spec = importlib.util.spec_from_file_location(modName, filePath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod





if __name__ == '__main__':
    main()