import os
import tempfile
from pyramid.threadlocal import get_current_registry
from oerpub.rhaptoslabs.swordpushweb.views.utils import Metadata
from oerpub.rhaptoslabs.sword2cnx import Connection

class Session(object):
    """ Base class for oerpub sessions. """

    def __init__(self):
        self._saveDir = None
        self._files = []
        self.metadata = None

    @property
    def canImportModule(self):
        """ Can the user import content from CNX, for example, can he edit
            an existing module? This should only return true if the user has
            sufficient permissions to download the module using sword. """
        return False

    @property
    def canUploadModule(self):
        """ Can the user upload new content to CNX? """
        return False

    @property
    def selectedWorkspace(self):
        return None

    @property
    def selectedWorkspaceTitle(self):
        return None

    def setSelectedWorkspace(self, ws):
        raise NotImplementedError, 'setSelectedWorkspace'

    def newSaveDir(self):
        self._saveDir = None
        self._files = []

    @property
    def saveDir(self):
        """ Create a save dir for this session the first time this property
            is accessed. This is where we will store temporary files part
            of this editing session. """
        if self._saveDir is None:
            tmp = get_current_registry().settings.transform_dir
            self._saveDir = tempfile.mkdtemp(dir=tmp)
        return self._saveDir

    @property
    def saveDirName(self):
        return os.path.basename(self.saveDir)

    @property
    def hasData(self):
        return self._saveDir is not None

    def addFile(self, filename, content):
        """ Add a file to our editing area, and keep track of it. """
        sd = self.saveDir
        fn = os.path.join(sd, filename)
        fp = open(fn, 'wb')
        try:
            fp.write(content)
        finally:
            fp.close()
            if not filename in self._files:
                self._files.append(filename)

    @property
    def files(self):
        return self._files

    @property
    def module_url(self):
        """ Return the url of the module on the remote site, when you are
            editing an existing module. """
        return None

    @module_url.setter
    def module_url(self, v):
        """ Set the url of the upstream module. """
        pass

class AnonymousSession(Session):
    """ Class for anonymous users. """

    username = 'anonymous'
    password = ''
    workspace_title = "Connexions"
    sword_version = "2.0"
    maxuploadsize = "0"
    collections = []

class TestingSession(AnonymousSession):
    pass

class CnxSession(Session):
    """ Class that stores information about a cnx user's login. """
    def __init__(self, username, password, service_document_url,
            workspace_title, sword_version, maxuploadsize, collections):
        super(CnxSession, self).__init__()
        self.username = username
        self.password = password
        self.service_document_url = service_document_url
        self.workspace_title = workspace_title
        self.sword_version = sword_version
        self.maxuploadsize = maxuploadsize
        self.collections = collections
        self.selected_workspace = 0
        self._module_url = None

    @property
    def canImportModule(self):
        return True

    @property
    def canUploadModule(self):
        return True

    @property
    def selectedWorkspace(self):
        try:
            return self.collections[self.selected_workspace]['href']
        except IndexError:
            return None

    @property
    def selectedWorkspaceTitle(self):
        try:
            return self.collections[self.selected_workspace]['title']
        except IndexError:
            return None

    def setSelectedWorkspace(self, ws):
        self.selected_workspace = 0
        for i, entry in enumerate(self.collections):
            if entry['href'] == ws:
                self.selected_workspace = i
                break

    @property
    def module_url(self):
        """ Return the url of the upstream module being edited in this session.
        """
        return self._module_url

    @module_url.setter
    def module_url(self, v):
        """ Set the url of the upstream module. """
        self._module_url = v
        conn = Connection(self.service_document_url,
                          user_name=self.username,
                          user_pass=self.password,
                          always_authenticate=True,
                          download_service_document=False)
        resource = conn.get_resource(content_iri = v)
        self.metadata = Metadata(resource.content, v,
            self.username, self.password)
