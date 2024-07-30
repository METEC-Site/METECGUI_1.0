import time

from Examples.CommandManager import b_Source_and_Dest as sd
from Framework.Manager.CommandManager import CommandManager


def main():
    cd = sd.CP()
    cs = sd.CommandSource()
    cm = CommandManager()
    cm.register(cd)
    cm.register(cs)
    cm.start()
    cd.start()
    cs.start()
    while True:
        time.sleep(10)
    pass

if __name__ == "__main__":
    main()