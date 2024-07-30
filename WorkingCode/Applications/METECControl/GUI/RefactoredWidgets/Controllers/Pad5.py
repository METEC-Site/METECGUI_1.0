from Applications.METECControl.GUI.RefactoredWidgets.Controllers.ControllerTypes import FourByThree


class CB5W(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-5W", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()

class CB5S(FourByThree):
    def __init__(self, GUIInterface, name=None, controllerName="CB-6C", parent=None, processGroups=None):
        FourByThree.__init__(self, GUIInterface, name=name, parent=parent, controllerName=controllerName, processGroups=processGroups)
        self.buildGUI()