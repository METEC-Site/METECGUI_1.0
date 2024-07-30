from Applications.METECControl.GUI.RefactoredWidgets.Controllers.ControllerTypes import FourByThree


class CB4W(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-4W", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()

class CB4S(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-4S", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()

class CB4T(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-4T", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()