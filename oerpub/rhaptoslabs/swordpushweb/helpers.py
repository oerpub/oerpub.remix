from pyramid.renderers import get_renderer
from pyramid.decorator import reify


from utils import check_login as utils_check_login
from utils import get_connection as utils_get_connection

class BaseHelper(object):

    def __init__(self, request):
        self.request = request
        self.session = self.request.session
        self.macro_renderer = get_renderer("templates/macros.pt")

    def check_login(self, raise_exception=True):
        return utils_check_login(self.request, raise_exception)

    def get_connection(self):
        return utils_get_connection(self.session)

    @reify
    def base(self):
        renderer = get_renderer("templates/base.pt")
        return renderer.implementation().macros['main']

