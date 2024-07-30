import inspect
import unittest


def abstractMethodCheck(abstractClass, subClass):
    # Get the abstractmethods defined in abstractClass
    absMethods = abstractClass.__abstractmethods__
    # Get all members (which will include method definitions) in subClass.  Turn it into a dict for easy access
    mems = dict(inspect.getmembers(subClass, inspect.isfunction))
    # Find the definitions in subClass for the abstract methods defined in abstractClass
    absMethodDefs = map(lambda x: mems[x], absMethods)
    # Get the __qualname__ of the subclass abstract method definitions.
    #   __qualname__ was introduced in Python 3.3, and provides a "dot qualified" name of nested classes, methods, and functions
    qualSubNames = map(lambda x: x.__qualname__, absMethodDefs)
    # Find the class for each qualSubName.  Include the function name for tracability.
    classNameForMethod = map(lambda x: (x.split('.')[0], x.split('.')[-1]), qualSubNames)
    # If any of the class names is the abstract class name, it has not been overridden
    absClassName = abstractClass.__qualname__
    unOverridden = list(filter(lambda x: x[0] == absClassName, classNameForMethod))

    if unOverridden:
        names = list(map(lambda x: x[1], unOverridden))
        str = "Abstract class: {}, subclass: {}, undefined abstract methods: {}".format(abstractClass, subClass, names)
        raise TypeError(str)
    return True

if __name__ == "__main__":
    unittest.main()