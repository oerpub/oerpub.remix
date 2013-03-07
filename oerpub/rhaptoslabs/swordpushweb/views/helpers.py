from pyramid.renderers import get_renderer
from pyramid.decorator import reify

from oerpub.rhaptoslabs.swordpushweb.interfaces import IWorkflowSteps
from utils import check_login as utils_check_login
from utils import get_connection as utils_get_connection

class BaseHelper(object):
    
    def __init__(self, request):
        """ Sets the following:
            request
            session
            macro renderer (check templates/macros.pt for more details. 
        """
        self.request = request
        self.session = self.request.session
        # this is not strictly necessary as we already add 'macros' to the
        # BeforeRenderEvent in ../subscribers.py
        self.macro_renderer = get_renderer("templates/macros.pt")
    
    def _process(self):
        self.check_login()

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

    def navigate(self):
        if self.request.get('workflownav.form.submitted', '') == 'submitted':
            action = self.get_next_action()
            if self.request.has_key('btn-back'):
                action = self.get_previous_action()
            self.request.response.redirect(action)    

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

    @reify
    def workflow_nav(self):
        return self.macro_renderer.implementation().macros['workflow_nav']

    def get_next_action(self):
        workflowsteps = self.request.registry.getUtility(IWorkflowSteps)
        wf_name = self.get_source()
        current_step = self.request.matched_route.name
        return workflowsteps.getNextStep(wf_name, current_step)

    def get_previous_action(self):
        workflowsteps = self.request.registry.getUtility(IWorkflowSteps)
        wf_name = self.get_source()
        current_step = self.request.matched_route.name
        return workflowsteps.getPreviousStep(wf_name, current_step)
    
    def get_batch_link(self, b_start, selected_workspace):
        params = {"b_start": b_start,
                  "workspace": selected_workspace}
        url = self.request.route_url(self.navigation_actions['batch'],
                                     _query=params)
        return url

    def set_source(self, source):
        self.request.session['source'] = source

    def get_source(self):
        return self.request.session.get('source', 'undefined')
    
    @reify
    def form_action(self):
        return self.request.matched_route.name
