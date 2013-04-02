from pyramid.renderers import get_renderer
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPFound

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

    def _navigate(self, errors, form, marker='workflownav.form.submitted'):
        # makes the rest of the lines a couple-a-chars shorter
        request = self.request
        if request.params.get(marker, '') == 'submitted':
            if request.params.has_key('btn-back'):
                action = self.get_previous_action()
                return HTTPFound(location=self.request.route_url(action))
            elif request.params.has_key('btn-forward'):
                # we cannot go forward in the process while there are errors
                if errors:
                    return None
                action = self.get_next_action()
                return HTTPFound(location=self.request.route_url(action))
        return None

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

    @reify
    def workflow_nav_form_begin(self):
        return self.macro_renderer.implementation().macros['workflow_nav_form_begin']

    @reify
    def workflow_nav_form(self):
        return self.macro_renderer.implementation().macros['workflow_nav_form']

    @reify
    def workflow_nav_form_end(self):
        return self.macro_renderer.implementation().macros['workflow_nav_form_end']

    def get_next_action(self, source=None, target=None, current_step=None):
        workflowsteps = self.request.registry.getUtility(IWorkflowSteps)
        source = source or self.get_source()
        target = target or self.get_target()
        current_step = current_step or self.request.matched_route.name
        return workflowsteps.getNextStep(source, target, current_step)

    def get_previous_action(self):
        workflowsteps = self.request.registry.getUtility(IWorkflowSteps)
        source = self.get_source()
        target = self.get_target()
        current_step = self.request.matched_route.name
        return workflowsteps.getPreviousStep(source, target, current_step)
    
    def get_batch_link(self, b_start, selected_workspace):
        params = {"b_start": b_start,
                  "workspace": selected_workspace}
        url = self.request.route_url(self.form_action, _query=params)
        return url

    def set_source(self, source):
        self.request.session['source'] = source

    def get_source(self):
        return self.request.session.get('source', 'undefined')
    
    def set_target(self, target):
        self.request.session['target'] = target

    def get_target(self):
        return self.request.session.get('target', 'undefined')
    
    @reify
    def form_action(self):
        return self.request.matched_route.name
