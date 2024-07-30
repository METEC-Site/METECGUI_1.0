import os

import matlab.engine

eng = matlab.engine.start_matlab()
filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), "Matlab"))
eng.addpath(filepath)

[ex1,ex2] = eng.example1(5, 10, nargout=2)
print(ex1)
print(ex2)

eng.quit()