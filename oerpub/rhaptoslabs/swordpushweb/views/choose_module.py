import os
import libxml2
import urlparse
import traceback
import formencode

from pyramid_simpleform import Form
from pyramid.decorator import reify
from pyramid.view import view_config

from oerpub.rhaptoslabs.cnxml2htmlpreview.cnxml2htmlpreview import \
    cnxml_to_htmlpreview
from oerpub.rhaptoslabs.swordpushweb.views.utils import (
    save_and_backup_file,
    save_zip,
    ConversionError)

from oerpub.rhaptoslabs import sword2cnx
from module_association import Module_Association_View

from utils import get_files
from utils import extract_to_save_dir


class ChooseModuleSchema(formencode.Schema):
    allow_extra_fields = True
    module_url = formencode.validators.URL()

class Choose_Module(Module_Association_View):

    @view_config(
        route_name='choose-module', renderer="templates/choose_module.pt")
    def process(self):
        super(Choose_Module, self)._process()
        self.do_transition()
        return self.navigate()

    def do_transition(self):
        request = self.request
        form = Form(request, schema=ChooseModuleSchema)
        if form.validate():
            module_url = form.data['module_url']
            request.session['source_module_url'] = module_url
            request.session['target_module_url'] = module_url
            self._download_module(module_url)
    
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
        
        save_dir = os.path.join(request.registry.settings['transform_dir'],
                                request.session['upload_dir'])
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
    def content_macro(self):
        return self.macro_renderer.implementation().macros['content_macro']

    @reify
    def back_step_label(self):
        return "&laquo; Back: Return to start page"
    
    @reify
    def next_step_label(self):
        return "Next: Edit selected module &raquo;" 

    @reify
    def next_step_title(self):
        source = self.session['source']
        if source == 'newemptymodule':
            return 'Add module description and save module to cnx.org'
        elif source == 'existingmodule':
            return 'Review module description and save module to cnx.org'
        elif source == 'importmodule':
              return 'Select whether this will be used for a new module or to override the contents of an existing module'
        return 'Select whether this will be used for a new module or to override the contents of an existing module'

    @reify
    def back_step_title(self):
        return "Return to the initial page"
