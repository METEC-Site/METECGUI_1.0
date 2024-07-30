from Applications.METECControl.GUI.RefactoredWidgets.Controllers.ControllerTypes import FourByThree, FiveByTwo


class CB2W(FourByThree):

    def __init__(self, GUIInterface, name=None, controllerName="CB-2W", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()


class CB2S(FourByThree):

    def __init__(self, GUIInterface, name=None, controllerName="CB-2S", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()

class CB2T(FiveByTwo):

    def __init__(self, GUIInterface, name=None, controllerName="CB-2T", parent=None, processGroups=None):
        FiveByTwo.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()