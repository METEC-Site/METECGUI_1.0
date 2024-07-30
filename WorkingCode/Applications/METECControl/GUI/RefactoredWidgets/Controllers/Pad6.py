from Applications.METECControl.GUI.RefactoredWidgets.Controllers.ControllerTypes import FourByThree


class CB6D(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-6D", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()

class CB6C(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-6C", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()

class CB6S(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-6S", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()