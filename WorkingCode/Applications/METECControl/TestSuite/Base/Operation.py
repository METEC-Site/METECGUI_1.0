from abc import ABC, abstractmethod

SingleOp = {
    "SetLevel": None, # emission level of the emission point. 2^n levels, where n is amount of flow controlling valves.
    "DeltaT": None, # amount of time that this valve should be open for, then after which the close command will be sent.
    "EmissionPoint": None # final emission point through which the flow will be routed.
}

class OperationABC(ABC):

    @abstractmethod
    def interpret(self):
        pass

class AtomicOperation(OperationABC):
    """ A class whose only operation is to set a single emission point to a single level."""
    def __init__(self, emissionPoint, setLevel):
        self.emissionPoint = emissionPoint
        self.setLevel = setLevel

    def interpret(self):
        print(f'Setting Emission Point {self.emissionPoint} to level {self.setLevel}')


class SinglePointEmission(OperationABC):
    """ Opening an emission point for a duration of time."""
    def __init__(self, setLevel=0, deltaT=10, emissionPoint=None, stopOnExit=True):
        OperationABC.__init__(self)
        self.setLevel = setLevel
        self.deltaT = deltaT
        self.emissionPoint = emissionPoint
        self.stopOnExit = stopOnExit
        self.operation = AtomicOperation(emissionPoint, setLevel)

    def interpret(self):
        self.operation.interpret()
        print(f'Waiting {self.deltaT} seconds until end of emission point {self.emissionPoint}')
        self.terminate()

    def terminate(self):
        print(f'End of emission reached. stopOnExit set to {self.stopOnExit}')
        if self.stopOnExit:
            print(f'closing Emission Point {self.emissionPoint}')
        else:
            print(f'Keeping Emission Point {self.emissionPoint} at level {self.setLevel}')
        print()


class IntermittentEmission(OperationABC):
    def __init__(self, emissionPoint=None, setLevel1=0, setLevel2=0, interval=10, repeats=3, stopOnExit=True):
        self.e1 = SinglePointEmission(setLevel1, deltaT=interval,emissionPoint=emissionPoint, stopOnExit=False)
        self.e2 = SinglePointEmission(setLevel2, deltaT=interval,emissionPoint=emissionPoint, stopOnExit=False)
        self.emissionPoint = emissionPoint
        self.repeats = repeats
        self.stopOnExit = stopOnExit

    def interpret(self):
        for i in range(0, self.repeats):
            self.e1.interpret()
            self.e2.interpret()
        self.terminate()

    def terminate(self):
        print(f'End of emission reached. stopOnExit set to {self.stopOnExit}')
        if self.stopOnExit:
            print(f'closing Emission Point {self.emissionPoint}')
        else:
            print(f'Keeping Emission Point {self.emissionPoint} at level {self.e2.setLevel}')
        print()