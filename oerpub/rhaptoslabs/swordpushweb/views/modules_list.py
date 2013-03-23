from z3c.batching.batch import Batch

from pyramid.decorator import reify
from pyramid.view import view_config

from utils import load_config
from helpers import BaseHelper
from module_association import get_module_list

class Modules_List_View(BaseHelper):

    """ Show a list of all the modules in a workspace.
    """
    @view_config(
        route_name='modules_list', renderer="templates/modules_list.pt")
    def generate_html_view(self):
        self.check_login()
        config = load_config(self.request)
        conn = self.get_connection()

        selected_workspace = self.session['collections'][0]['href']
        selected_workspace = self.request.params.get('workspace',
                                                     selected_workspace)
        print "Workspace url: " + selected_workspace

        modules = get_module_list(conn, selected_workspace)
        b_start = int(self.request.GET.get('b_start', '0'))
        b_size = int(self.request.GET.get('b_size', 
                                          config.get('default_batch_size')))
        modules = Batch(modules, start=b_start, size=b_size)

        response = {'selected_workspace': selected_workspace,
                    'modules': modules,
                    'request': self.request,
                    'config': config,
                    'view': self,
        }
        return response

    @reify
    def modules_list(self):
        return self.macro_renderer.implementation().macros['modules_list']


