REQUIRES python 3.6

CommandFramework contains the modules in:
Framework
UnitTests
Utils
UtilTests
Docs

Operating the Framework:

    Main.py:
        OVERVIEW

            This Framework is intended to use a module, located at Framework/Main.py, to operate. This Main acts as a
            bootstrapper of sorts; it connects the modules, instantiates the Archiver, Managers, and Workers, and then
            starts them. It will then run an kickoff 'INIT' method if supplied in the config, which will be the last thing
            to run before the main goes into its main loop.
            The main requires a config file as a command line argument. This should be a path to a config file, the format
            of which is described below under CONFIG. The main will act as a factory, instantiating and starting each class
            in turn with the provided arguments (and sometimes others, as described under INSTANTIATION.) Then, the INIT
            method will be called (or not, if left out).

        CONFIG
            To instantiate properly, the main.py file needs a config file to act as a bootstrapper to create instances
            and connect the managers to the workers, among other things. This config file will contain a dictionary
            (must be named configDict if using python as the file). This dictionary will contain the following fields to instantiate
            objects. Each field must have a 'module' and 'class' key, which is what python uses to find the module where the
            class is located. The framework will then use this class definition to create an instance, passing in all other
            key/value pairs located within the dictionary. An example is provided below to serve as a template.

            'Workers':[...,
            'worker1': {
                'module': 'Framework.BaseClasses.ExampleWorkerModule',
                'class': 'ExampleWorkerClass',
                'kwarg1': 'value1',
                'kwarg2': ['expected', 'values', 'for', 'kwarg2'],
                'kwarg3': 42},
            ...]

            The main.py will pass in ALL kwargs to the instance, including class and module, as well as the archiver,
            commandManager, dataManager, and eventManager to all workers. Since python requires a 1:1
            pass for all named parameters, any that are passed in but don't have a parameter within the class instance definition
            may cause an error. Therefore, within class definition __init__ method, it is recommended to include a **kwargs
            to catch the extra parameters. An example is provided below.

            Located in Framework.BaseClasses.ExampleWorkerModule:

            class ExampleWorkerClass:
                def __init__(self, archiver, commandManager, dataManager, eventManager, name, kwarg1=1, kwarg2=[1,2,3,4],
                             kwarg3=42, **kwargs):
                             # code for init method


            The config used in the Main must come in a specified format. It is a dictionary with 5-6 fields:
                namespace: string
                Archiver: dict (singleton)
                CommandManager: dict (singleton)
                DataManager: dict (singleton)
                EventManager: dict(singleton)
                Workers: list of dicts (0-many)
                Init: dict (0-1)

            Each of the above keys will have a field, either a dictionary or list of dictionaries, that provide a the main
            with a template to instantiate the object. Each factory dictionary must contain a 'module' and 'class' field,
            which is the path to the python module/class definition. The keywords following the class definition will be
            passed to the class for instantiation. In addition, the Managers each will receive a reference to the
            Archiver, and the workers will all get a reference to the Archiver and each manager. Then, once the Archiver,
            Command/Data/Event Manager (all singletons) and Workers are instantiated, the Init method is called in much
            the same way the method/class definitions are, only with no keyword arguments.

        INITIALIZATION

            The order of instantiation of the class types will ALWAYS be:
            1) Archiver
                This is done to ensure that all data, metadata, logs, etc are captured first and foremost.
            2) Managers
                Included in this framework are the Command, Data, and Event managers. For keyword arguments, the managers
                 need a Unique name and a reference to the directory archiver.
            3) Workers
                Workers are passed a reference to the Archiver and Managers (as well as other keyword arguments which
                may be supplied), and therefore must be instantiated last.
            4) Init (OPTIONAL)
                The init method will be instantiated last of all objects (if at all), and will be the last thing in
                Main.py to run before the main loop.
            5) Once the shutdown event is raised or control C is pressed (if using command line), then the program will
                enter into shutdown. 'end' will be called on all visible workers, and resources will be freed before the
                program finally closes.

        UBIQUITOUS METHODS:
            There are a few methods that are ubiquitious throughout the framework.

            start:
            The first is 'start'; every object that is provided in the config must have a [class].start() method. This is
            called by the Main to, well, start the method or class. Implementation of this method is left up to the
            class itself. Many times it will start the class's threading mode, executing the run method.

            accept:
            In order to obtain packages from other threads or objects, the class needs to have an 'accept' method. In
            non-threaded mode, this will generally call the handlePackage method of the class on that package, and in
            threaded mode, accept will generally put that package on the object's internal queue so that object can
            handle it in its own event loop.

            handlePackage:
            To obtain useful data, execute a command, or parse an event, an object must have a 'handlePackage' method.
            Implementation of this is left up to the class definition. IE if an object is expecting to receive a data
            package

            end:
            The 'end' method is a special command that instructs the instance to end all tasks and exit cleanly. On destnations,
            for example, this will set the terminate flag to True and run through all packages on the queue, eventually breaking
            from the accept loop. After this is done, _onExitCleanup is called to finally unallocate any resources/close files/etc.

            _onExitCleanup:
            The final method called that will cease function of an instance. It is similar to a destructor, though implementation
            is left up to the creator of the module/class. It should free resources, release locks, and do whatever cleanup
            is necessary before the program ends.


        ARCHIVER
            Overview:
            The Directory Archiver is a singleton within the framework; there is only one of it, and it is the first
            object to be instantiated. It acts as the storage unit for all data, event, command, metadata, logfiles,
            configs, etc. It will receive packages from the Data Manager, Event Manager, and Command manager and store
            them based on their source and ChannelType.

            Base Dir:
            The archiver is instantiated with a 'Base Directory'. This directory is where all archives will be stored,
            one directory per rollover. For example, on the most basic implementation of the archiver, the baseDir is set
            to be '[somepath]/[basedir]', and the subdirectory for that rollover period will be '/[datetime]'. The whole
            path is '[somepath]/[basedir]/[datetime]', and after collecting records for the entire period, the archiver
            will rollover. After the rollover period (default is one day), the archiver will close all existing records,
            and put all new records in a new folder with the same root ('[somepath]/[basedir]/[datetime + 1 day]').

            Rollover:
            The Directory archiver has a built in check for when it should rollover; a time based rollover, and a size
            based rollover. The kw parameters will be passed onto a rollover manager delegate,

                KW parameters:
                - currentDir: current path of the directory.
                - utcStartHMS: start time of the directory. (in 'H:M:S' format in UTC)
                - rolloverInterval: Either time (seconds), or size (bytes).
                - rolloverCriteria: 'time' or 'size', describes which type of rollover to use.

            If using the size, the rollover manager will monitor the size of the directory and if it is over the size
            limit. If the size is greater than the rolloverInterval, the manager will signal a rollover.
            If using time, the rollover manager checks the current time with the start time (default to the moment
            the Directory was created) and if the time delta is greater than the rolloverInterval (seconds), the manager
            will signal a rollover.

            Channels:
            Each channel of a package will be sent to a different subdirectory, based on the 'CHANNEL_TYPES' mapping
            within DirectoryArchiver. Data is sent to '[basedir]/[day archive]/data', logs sent to
            '[basedir]/[day archive]/logs', etc. Within each of those channel subfolders, each channel will have its own
            file (if applicable). Each package with that matching channel type/name will be written to that file.

            Configs:
            During the instantiation of the archiver, it can be given a number of config files. These files will be
            copied into the directory, using the provided information within the supplied config dictionary.
            The information to provide the correct route to the config file is as follows:
            {'channel': unique name of the config channel to be used by other objects to read the config.
             'basePath': path from root to the base directory of the config file.
             'subPath': path from the base path to the subdirectory where the config file is located.
             'fileName': filename of the config}
            The config file, upon Archiver instantiation, will be stored under [Archiver Base]/config/[subPath]/[fileName]
            (IE the [basePath] provided in the config dictionary will be replaced with the path [Archiver Base]/config).
            Any worker or manager can request to read this config file by calling readConfig on the Archiver, and passing
            the proper channel name.

        MANAGERS
            The managers are singletons, much the same way as the Archiver.
            Command -
                The Command Manager will accept any command packages, and deliver it to destinations that match the
                signature included in the payload (their unique names must match and the provided method must exist in
                the destination object)
            Data -
                The Data Manager will shepherd data from any object that delivers to it a package, and send it to any
                of its destinations (it will always send it to the archiver).
            Event -
                The Event Manager will accept any event package generated by publishing objects, and send those event
                packages to any object that subscribes to those event types/event sources.


        WORKERS
            Workers are objects that have access to all managers and the Directory Archiver. A worker is a destination,
            meaning it has an 'accept' method. Also, it will typecheck all managers and the archiver to ensure that it
            is either passed a None or an object of that type; this will ensure proper instantiation and typing of all
            objects in the framework.


        INIT
            If provided, after all objects have been instantiated the method/class provided by the INIT dictionary is
            run. It will 'kick off' the program, and is useful for logging the moment when the program started, or for
            creating the QT event loop (which blocks/uses the main loop, preventing main from progressing while it is
            active).


    PACKAGES
        Packages are the objects used between objects; they are sent around via an object's 'accept' method.
        Every package has the following attributes:
           - a source, a text string which matches the name of the object
        (usually a worker) that created it;
           - a ChannelType associated with it( Data, Event, Command, etc.
             as enumerated in the Framework/Channels.py module). These channels will be used to inform what each
             package contains and how it is to be treated by recipients.
           - a payload
            The deliverable the package wraps. Can be any object, though is usually a custom Payload object or a dictionary.
           - a timestamp
            An epoch timestamp, usually marking when the package was created.
           - a package ID
            Each package should have a unique ID, as provided upon its instantiation.


    READERS
        Readers are classes with a read method, and tend to send data around the framework. Any data payload sent to
        the archiver requires the reader to have registered with the archiver beforehand. This tells the archiver
        what fields to expect, and allows it to write headers with the proper metadata (as described below).

        METADATA
        Metadata in this context is information about the fields provided by a read(). It can come in two forms, one
        simpler dictionary and another custom Metadata class (under Framework.BaseClasses.Metadata). If using a dictionary,
        each field supplied by a read must be a key in the dictionary, with its value being the type expected by the read.
        IE if one is using 'field1' and its type is 'int', then within the metadata dictionary must exist a key/value pair

        {..., 'field1': 'int',...}

        The other metadata available for use is Metadata custom class. Similar to the dictionary method, it is mutable and
        addressable like a dictionary. Also, it uses keys in the same way (IE each field from a read must exist as a key
        in the Metadata). However, the value of a specific key is not a simple string; it is a dictionary with any number of its own fields.
        The metadata keys required by the archiver are 'type', and any other fields in the metadata for a field will
        be saved at the top of a csv as the header. Example of a metadata mutable, in dictionary representation, follows.

        {...,
         'field1': {'type': 'int', 'notes': 'this is the metadata for field1', 'units': 'field1units'},
         ...}

        If using metadata, it is recommended to use the ClassUtils method isMetadata to differentiate between the
        dictionary and custom types.

    CHANNELTYPE
        This custom class accompanies each package sent in the framework, and is used primarily as a tag to determine
        how the payload is to be handled. A package that contains data (which should be a dictionary) will have the
        ChannelType.Data tag, and a command sent through the CommandManager will have the ChannelType.Command tag.


    THREADING
        The modules here operate under the principle of Threading; Multiple different threads, with their own scopes
        and timings exist within one Program/Process. This speeds up processing and allows for many things to happen
        at once in a non-blocking manner. This is done with python's threading module, and allows for concurrent operation.
        To get access to another instance's thread, put a package onto its pipe. This is commonly done through Framework
        Managers, specifically the CommandManager. For example, to send a 'read' command to an instance, a package
        with type 'ChannelType.Command' must be sent to the CommandManager with a specific payload. That payload must have
        the destination matching the name of the instance that is to accept the command, as well as the method to be
        invoked. If that destination has registered with the command manager before, the package will be sent to the
        instance to be invoked. That destination must have 1) an accept method, 2) a handlePackage method, 3) this
        handle package method must be set up so as to accept external commands and execute them (inherit from
        commandClass and within handlePackage, call executeCommand(command) on the package and payload).

        Another example: Lets say a GUI wants to receive data from an instance of a reader. The reader must be set to
        send data to the DataManager, and the GUI should subscribe to the DataManager, requesting all data from that
        source. Once this occurs, if the datamanager receives a data package from the reader, this will be sent to
        the GUI's accept method, which will call handlePackage on the package. The data manager will then be able to
        manipulate and parse that data any way it would like.

    QT and GUI Information
