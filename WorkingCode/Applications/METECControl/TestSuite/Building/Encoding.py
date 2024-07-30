SingleOp = {
    "SetLevel": None, # emission level of the emission point. 2^n levels, where n is amount of flow controlling valves.
    "DeltaT": None, # amount of time that this valve should be open for, then after which the close command will be sent.
    "EmissionPoint": None # final emission point through which the flow will be routed.
}

class OperationBaseClass():
    def __init__(self):
        self.setLevel = None
        self.deltaT = None
        self.emissionPoint = None

    def formatOp(self):
        return {
            "SetLevel": self.setLevel,
            "DeltaT": self.deltaT,
            "EmissionPoint": self.emissionPoint
        }

    def save(self):
        pass

