from Applications.METECControl.GUI.RefactoredWidgets.Controllers.ControllerTypes import FourByThree, FiveByTwo


class CB1W(FourByThree):

    def __init__(self, GUIInterface, name=None, controllerName="CB-1W", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName,processGroups=processGroups)
        self.buildGUI()


class CB1S(FourByThree):

    def __init__(self, GUIInterface, name=None, controllerName="CB-1S", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()

class CB1T(FiveByTwo):

    def __init__(self, GUIInterface, name=None, controllerName="CB-1T", parent=None, processGroups=None):
        FiveByTwo.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()