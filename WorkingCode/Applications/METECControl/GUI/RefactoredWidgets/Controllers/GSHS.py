from Applications.METECControl.GUI.RefactoredWidgets.Controllers.ControllerTypes import GSHController

class GSH1(GSHController):

    def __init__(self, GUIInterface, name=None, controllerName="GSH-1", parent=None, processGroups=None):
        GSHController.__init__(self, GUIInterface, name=name, parent=parent, processGroups=processGroups, controllerName=controllerName)
        self.buildGUI()
        self.buildAdhocController(1)



class GSH2(GSHController):

    def __init__(self, GUIInterface, name=None, controllerName="GSH-2", parent=None, processGroups=None):
        GSHController.__init__(self, GUIInterface, name=name, parent=parent, processGroups=processGroups, controllerName=controllerName)
        self.buildGUI()
        self.buildAdhocController(2)

class GSH3(GSHController):

    def __init__(self, GUIInterface, name=None, controllerName="GSH-3", parent=None, processGroups=None):
        GSHController.__init__(self, GUIInterface, name=name, parent=parent, processGroups=processGroups, controllerName=controllerName)
        self.buildGUI()
        self.buildAdhocController(3)

class GSH4(GSHController):

    def __init__(self, GUIInterface, name=None, controllerName="GSH-4", parent=None, processGroups=None):
        GSHController.__init__(self, GUIInterface, name=name, parent=parent, processGroups=processGroups, controllerName=controllerName)
        self.buildGUI()
        self.buildAdhocController(4)