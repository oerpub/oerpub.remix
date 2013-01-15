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
        """ Sets the following:
            request
            session
            macro renderer (check templates/macros.pt for more details. 
            source
        """
        self.request = request
        self.session = self.request.session
        self.macro_renderer = get_renderer("templates/macros.pt")
        self.source = 'undefined'
        if request.POST and 'source' in request.POST: 
          self.source = request.POST['source']
        elif request.GET and 'source' in request.GET: 
          self.source = request.GET['source']

    def check_login(self, raise_exception=True):
        """ Default login behaviour.
            It wraps utils.check_login and returns True or False.
        """
        return utils_check_login(self.request, raise_exception)

    def get_connection(self):
        """ Wraps utils.get_connection.
            The returned connection is a sword2cnx.Connection

            TODO:
            Add a proper interface to sword2cnx so we can rather assert that
            interface where necessary.
        """
        return utils_get_connection(self.session)

    @reify
    def base(self):
        """ Base macro renderer.
            Useful when creating new templates. Have a look at templates/base.pt
            for more details.
        """
        renderer = get_renderer("templates/base.pt")
        return renderer.implementation().macros['main']

    @reify
    def back_navigation_warning(self):
        return self.macro_renderer.implementation().macros['back_navigation_warning']

    @reify
    def forward_navigation_warning(self):
        return self.macro_renderer.implementation().macros['forward_navigation_warning']

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

    def get_source(self):
        return self.source
