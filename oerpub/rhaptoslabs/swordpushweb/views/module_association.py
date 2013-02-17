import lxml
import formencode

from z3c.batching.batch import Batch

from pyramid.decorator import reify
from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid.renderers import get_renderer
from pyramid_simpleform.renderers import FormRenderer

from oerpub.rhaptoslabs import sword2cnx

from utils import load_config
from helpers import BaseHelper

class ModuleAssociationSchema(formencode.Schema):
    allow_extra_fields = True
    module = formencode.validators.String()


class Module_Association_View(BaseHelper):

    # NOTE: Your implementation class *must* define these actions if you want
    # to reuse the navigation and batch macros.
    navigation_actions = {'next': 'metadata', 
                          'previous': 'preview',
                          'batch': 'module_association'}

    @view_config(route_name='module_association',
                 renderer='templates/module_association.pt')
    def generate_html_view(self):
        request = self.request

        self.check_login()
        config = load_config(request)
        conn = self.get_connection()

        workspaces = [
            (i['href'], i['title']) for i in self.session['collections']
        ]
        selected_workspace = request.params.get('workspace', workspaces[0][0])
        workspace_title = [w[1] for w in workspaces if w[0] == selected_workspace][0]

        b_start = int(request.GET.get('b_start', '0'))
        b_size = int(request.GET.get('b_size', config.get('default_batch_size')))

        modules = get_module_list(conn, selected_workspace)
        modules = Batch(modules, start=b_start, size=b_size)
        module_macros = get_renderer('templates/modules_list.pt').implementation()

        form = Form(request, schema=ModuleAssociationSchema)
        response = {'form': FormRenderer(form),
                    'workspaces': workspaces,
                    'selected_workspace': selected_workspace,
                    'workspace_title': workspace_title,
                    'modules': modules,
                    'request': request,
                    'config': config,
                    'module_macros': module_macros,
                    'view': self,
        }
        return response

    @reify
    def macros(self):
        return self.macro_renderer.implementation().macros

    @reify
    def workspace_list(self):
        return self.macro_renderer.implementation().macros['workspace_list']

    @reify
    def workspace_popup(self):
        return self.macro_renderer.implementation().macros['workspace_popup']

    @reify
    def modules_list(self):
        return self.macro_renderer.implementation().macros['modules_list']


def get_module_list(connection, workspace):
    xml = sword2cnx.get_module_list(connection, workspace)
    tree = lxml.etree.XML(xml)
    ns_dict = {'xmlns:sword': 'http://purl.org/net/sword/terms/',
               'xmlns': 'http://www.w3.org/2005/Atom'}
    elements =  tree.xpath('/xmlns:feed/xmlns:entry', namespaces=ns_dict)

    modules = []
    for element in elements:
        title_element = element.xpath('./xmlns:title', namespaces=ns_dict)[0]
        title = title_element.text

        link_elements = element.xpath('./xmlns:link[@rel="edit"]',
                                      namespaces=ns_dict
                                     )
        edit_link = link_elements[0].get('href')

        path_elements = edit_link.split('/')
        view_link = '/'.join(path_elements[:-1])
        path_elements.reverse()
        uid = path_elements[1]

        modules.append([uid, edit_link, title, view_link])
    return modules

