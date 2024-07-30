import importlib.util
import os
import sys
import unittest

from Framework.Manager.ObjectManager import ObjectManager
from Utils import ClassUtils as cu


def CleanNamespace(namespace):
    def unitTestNamespace(fn):
        def innerFunc(self, *args, **kwargs):
            try:
                ObjectManager.setProcessNamespace(namespace)
                fn(self, *args, **kwargs)
            finally:
                ObjectManager.endNamespace(namespace)
        return innerFunc
    return unitTestNamespace

def main():
    unitTestDir = os.path.dirname(sys.argv[0])
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