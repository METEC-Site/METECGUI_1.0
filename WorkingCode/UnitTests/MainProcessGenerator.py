import os
import sys

from Framework import Main


def mainProcess():
    configPath = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "config.py"))
    sys.argv.insert(1, '-c')
    sys.argv.insert(2, configPath)
    Main.main()
    sys.argv.pop(1)
    sys.argv.pop(2)