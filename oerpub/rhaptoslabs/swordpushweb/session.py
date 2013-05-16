class Session(object):
    """ Base class for oerpub sessions. """

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
        self.username = username
        self.password = password
        self.service_document_url = service_document_url
        self.workspace_title = workspace_title
        self.sword_version = sword_version
        self.maxuploadsize = maxuploadsize
        self.collections = collections
        self.selected_workspace = 0

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
