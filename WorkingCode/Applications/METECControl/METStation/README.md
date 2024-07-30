# Titanic Setup

##Background
 This readme is intended to help set up TITANIC to run in Python. The TITANIC module is developed by NREL 
 to provide analysis of meteorological data. 

 You can access it by following the below link to the git repository: 

 https://github.com/NREL/TITANIC

##Method 1
 Using the Matlab module.

### Prerequisites: 
    matlab engine module.
    MATLAB installation (R2014b or later)
 
###Installing matlab engine:
 https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html

 In short, follow the below steps:
 1) Open MATLAB
 2) Type matlabroot in command window, and copy the result (referred to as {matlabroot})
 3) Depending on the operating system, open a terminal and enter the following (you may need admin privileges):
    a) Windows:
        
        cd "{matlabroot}\extern\engines\python"
        python setup.py install
    b) macOS or linux:
       
        cd "{matlabroot}/extern/engines/python"
        python setup.py install
    c) At matlab command prompt:
       
        cd (fullfile(matlabroot,'extern','engines','python'))
        system('python setup.py install')
 4) Within your python code, call the following code before executing any imported matlab libraries.
 
        import matlab.engine
        eng = matlab.engine.start_matlab()
 5) Within python code, add the paths to the folder where the matlab code is held so the engine knows where to look.
 
        folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "Matlab"))
        eng.addpath(folder)

##Method 2
Compiling Matlab code into a library that can be run in python