from Applications.METECControl.GUI.RefactoredWidgets.Controllers.ControllerTypes import FourByThree


class CB7P1(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-7P1", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()

class CB7P2(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-7P2", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()

class CB7P3(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-7P3", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName,
                             processGroups=processGroups)
        self.buildGUI()

class CB7P4(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-7P4", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()