from Framework.BaseClasses.Commands import CommandClass, CommandMethod


class DecoratedClass(CommandClass):
    def __init__(self, name='Decorated Class'):
        CommandClass.__init__(self, name)
        self.name = name
        pass


    def getCPMetadata(self):
        if '_visibleCommands' in self.__dict__:
            return self._visibleCommands
        else:
            return []

    @CommandMethod
    def decoratedFunction(self):
        print('This function has been decorated')

    def execute(self, package):
        command = package.payload


def main():
    dec = DecoratedClass()
    dec.decoratedFunction()


if __name__ == "__main__":
    main()