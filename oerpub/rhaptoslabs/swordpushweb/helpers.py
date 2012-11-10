from pyramid.renderers import get_renderer
from pyramid.decorator import reify


from utils import check_login as utils_check_login
from utils import get_connection as utils_get_connection

class BaseHelper(object):
    
    # NOTE: Your implementation class *must* define these 2 actions or
    # any macros that depend on them for creating navigation links will fail.
    navigation_actions = {'next': None, 
                          'previous': None,
                          'batch': None}

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

    def get_next_action(self):
        url = self.request.route_url(self.navigation_actions['next'])
        return url

    def get_previous_action(self):
        url = self.request.route_url(self.navigation_actions['previous'])
        return url
    
    def get_batch_link(self, b_start, selected_workspace):
        params = {"b_start": b_start,
                  "workspace": selected_workspace}
        url = self.request.route_url(self.navigation_actions['batch'],
                                     _query=params)
        return url
