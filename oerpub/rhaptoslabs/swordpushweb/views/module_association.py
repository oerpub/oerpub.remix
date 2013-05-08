import os
import lxml
import libxml2
import urlparse
import traceback
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
from utils import (
    get_files,
    get_save_dir,
    create_save_dir,
    extract_to_save_dir,
    cleanup_save_dir)
from oerpub.rhaptoslabs.swordpushweb.views.utils import (
    save_and_backup_file,
    save_zip,
    ConversionError)
from oerpub.rhaptoslabs.cnxml2htmlpreview.cnxml2htmlpreview import \
    cnxml_to_htmlpreview



class ChooseModuleSchema(formencode.Schema):
    allow_extra_fields = True
    module_url = formencode.validators.URL()

class Module_Association_View(BaseHelper):

    @view_config(route_name='module_association',
                 renderer='templates/module_association.pt')
    def process(self):
        super(Module_Association_View, self)._process()
        self.do_transition()
        return self.navigate()
    
    def do_transition(self):
        request = self.request
        form = Form(request, schema=ChooseModuleSchema)
        cleanup_save_dir(request)
        if form.validate():
            selected_workspace = form.data['workspace']
            self.set_selected_workspace(selected_workspace)
            module_url = form.data['module_url']
            request.session['source_module_url'] = module_url
            request.session['target_module_url'] = module_url
            self._download_module(module_url)
    
    def navigate(self, errors=None, form=None):
        view = super(Module_Association_View, self)._navigate(errors, form)
        if view:
            return view 

        request = self.request
        config = load_config(request)
        conn = self.get_connection()

        workspaces = [
            (i['href'], i['title']) for i in self.session['collections']
        ]
        selected_workspace = self.get_selected_workspace()
        workspace_title = self.get_selected_workspace_title()

        b_start = int(request.GET.get('b_start', '0'))
        b_size = int(request.GET.get('b_size', config.get('default_batch_size')))

        modules = get_module_list(conn, selected_workspace)
        modules = Batch(modules, start=b_start, size=b_size)
        module_macros = get_renderer('templates/modules_list.pt').implementation()
        dialog_macros = get_renderer('templates/dialogs.pt').implementation()

        form = Form(request, schema=ChooseModuleSchema)
        response = {'form': FormRenderer(form),
                    'workspaces': workspaces,
                    'selected_workspace': selected_workspace,
                    'workspace_title': workspace_title,
                    'modules': modules,
                    'request': request,
                    'config': config,
                    'module_macros': module_macros,
                    'dialog_macros': dialog_macros,
                    'view': self,
        }
        return response

    def _download_module(self, module_url):
        request = self.request
        session = request.session
        conn = sword2cnx.Connection(session['service_document_url'],
                                    user_name=session['username'],
                                    user_pass=session['password'],
                                    always_authenticate=True,
                                    download_service_document=False)

        parts = urlparse.urlsplit(module_url)
        path = parts.path.split('/')
        path = path[:path.index('sword')]
        module_url = '%s://%s%s' % (parts.scheme, parts.netloc, '/'.join(path))

        # example: http://cnx.org/Members/user001/m17222/sword/editmedia
        zip_file = conn.get_cnx_module(module_url = module_url,
                                       packaging = 'zip')
         
        save_dir = get_save_dir(request)
        if save_dir is None:
            request.session['upload_dir'], save_dir = create_save_dir(request)
        extract_to_save_dir(zip_file, save_dir)

        cnxml_file = open(os.path.join(save_dir, 'index.cnxml'), 'rb')
        cnxml = cnxml_file.read()
        cnxml_file.close()
        conversionerror = None
        try:
            htmlpreview = cnxml_to_htmlpreview(cnxml)
            save_and_backup_file(save_dir, 'index.html', htmlpreview)
            files = get_files(save_dir)
            save_zip(save_dir, cnxml, htmlpreview, files)
        except libxml2.parserError:
            conversionerror = traceback.format_exc()
            raise ConversionError(conversionerror)

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

    @reify
    def back_step_label(self):
        return "&laquo; Back: Return to preview page"
    
    @reify
    def next_step_label(self):
        return "Next: Describe module &raquo;" 

    @reify
    def next_step_title(self):
        source = self.session['source']
        if source == 'newemptymodule':
            return 'Add module description and save module to cnx.org'
        elif source == 'existingmodule':
            return 'Review module description and save module to cnx.org'
        return 'Add module description and save module to cnx.org'

    @reify
    def back_step_title(self):
        return "Return to the preview page"


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

        # element can either be a module or collections
        # want modules and not collections
        if uid.startswith('m') or uid.find('module') >= 0:
            modules.append([uid, edit_link, title, view_link])
    return modules
