from Applications.METECControl.GUI.RefactoredWidgets.Controllers.ControllerTypes import FourByThree, FiveByTwo


class CB3W(FourByThree):

    def __init__(self, GUIInterface, name=None, controllerName="CB-3W", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()


class CB3S(FourByThree):

    def __init__(self, GUIInterface, name=None, controllerName="CB-3S", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()

class CB3T(FiveByTwo):

    def __init__(self, GUIInterface, name=None, controllerName="CB-3T", parent=None, processGroups=None):
        FiveByTwo.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()