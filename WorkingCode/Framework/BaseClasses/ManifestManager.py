# from Framework.BaseClasses.FrameworkObject import FOMetaclass, FrameworkObject # commented out to transition to Frameworkv2
from Framework.BaseClasses.Registration.FrameworkRegistration import FrameworkObject

from Utils import FileUtils as fUtils
from Utils import TimeUtils as tu


class ManifestManager(FrameworkObject):
    def __init__(self, archiver=None, commandManager=None, dataManager=None, eventManager=None,
                 name="ManifestManager", manifestPaths:dict =None, **kwargs):
        """
        configPaths: dictionary of configName to path where the summary exists in the file system.
        """
        FrameworkObject.__init__(self, name=name)
        if manifestPaths is None:
            manifestPaths = {}
        self._allManifests = {}
        for name, pathToManifest in manifestPaths.items():
            self.addManifest(name, pathToManifest)

    def start(self):
        return True

    def end(self):
        return True

########################################################################################################################
############################## Methods for adding, removing, and loading manifests #####################################
########################################################################################################################

    def addManifest(self, manifestName, pathToManifest):
        """ Adds a new manifest with a new summary loaded from the path located in pathToManifest.

        """
        if manifestName in self._allManifests.keys():
            raise NameError(f'Manifest named {manifestName} already exists. Either remove the existing manifest, or call updateManifest.')
        man = self._loadManifestFile(pathToManifest)
        self._allManifests[manifestName] = man

    def _loadManifestFile(self, pathToManifest):
        manifest = fUtils.loadSummary(pathToManifest)
        return manifest

    def updateManifest(self, manifestName, pathToManifest):
        """ Updates an existing manifest with a new summary loaded from the path located in pathToManifest.

        """
        if not manifestName in self._allManifests.keys():
            raise Exception(f'Manifest named {manifestName} does not exist, and cannot be updated. Try calling addManifest instead.')
        self.removeManifest(manifestName)
        self.addManifest(manifestName, pathToManifest)

    def removeManifest(self, manifestName):
        if not manifestName in self._allManifests.keys():
            raise Exception(f'Manifest named {manifestName} does not exist, and cannot be removed.')

    def getManifest(self, manifestName):
        return self._allManifests.get(manifestName, None)


########################################################################################################################
################################# Methods for accessing currently loaded manifests #####################################
########################################################################################################################

    def retrieveRecord(self, manifestName, timestamp=None):
        if timestamp is None:
            timestamp = tu.MAX_EPOCH
        if not manifestName in self._allManifests.keys():
            raise Exception(f'Manifest named {manifestName} does not exist in loaded manifests.')
        manifest = self._allManifests[manifestName]
        if manifest is None:
            return None
        priorTimestamps = list(filter(lambda x: x <= timestamp, manifest.keys()))
        sortedPriorTimestamps = sorted(priorTimestamps)
        if len(sortedPriorTimestamps) == 0:
            cfgAtTS = None
        else:
            cfgAtTS = manifest[sortedPriorTimestamps[-1]]
        return cfgAtTS

    def retreiveLoadedRecord(self, manifestName, timestamp=None):
        rec = self.retrieveRecord(manifestName, timestamp=timestamp)
        if rec:
            return rec["LoadedRecord"]
        return None
