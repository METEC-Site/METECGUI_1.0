class BufferError(Exception):
    pass

class IsNoneError(Exception):
    pass

class ConfigurationError(Exception):
    pass

class LoadError(Exception): # error when loading a file,
    pass

# Error when expecting an object to be a certain class but it is not that class or is not a child class of the original.
class InheritError(Exception):
    pass

class ThreadEndedError(Exception):
    pass

class PathExistsError(Exception):
    pass

class ManifestError(Exception):
    pass

class InstanceError(Exception): # error for when an instance is expected but does not exist
    pass

class ResourceAllocationError(Exception):
    pass

class MetadataMissingError(Exception): # Used when somethine expects metadata to exist but it doesn't.
    pass

# base exception for if something already exists and an operation would result in a conflict between old/new versions.
class ConflictError(Exception):
    pass

class ArchiveConfilctError(ConflictError): # exception for when an archive already exists at a given path.
    pass

# class for when a set of metadata doesn't match the corresponding payload (specifically keys)
class MetadataMismatchError(ConflictError):
    pass

class ResourceConflictError(ConflictError):
    pass

# Error for when something tries to get a unique name but that name already belongs to something else.
class NameConflict(ConflictError):
    pass

class InstanceConflict(ConflictError):
    pass



class ExistsError(Exception): # used when trying to access something that doesn't exist.
    pass

class PinExistsError(ExistsError): # error when pin does not exist. Specifically for Labjack.
    pass

class FieldExistsError(ExistsError): # error raised when field does not exist.
    pass

class ChannelExistsError(ExistsError): # used when the channel specified does not exist
    pass

class FormatterExistsError(ExistsError): # used when a formatter should exist within an archiver/InstanceIO but it doesn't.
    pass

class NameExistsError(ExistsError):
    pass