import os
import libxml2
import urlparse
import traceback
import formencode

from pyramid.decorator import reify
from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid_simpleform.renderers import FormRenderer

from oerpub.rhaptoslabs import sword2cnx

from oerpub.rhaptoslabs.cnxml2htmlpreview.cnxml2htmlpreview import cnxml_to_htmlpreview

from helpers import BaseHelper 
from ..editor import EditorHelper
from oerpub.rhaptoslabs.swordpushweb.views.utils import (
    save_and_backup_file,
    save_zip,
    ConversionError)

from utils import get_files
from utils import extract_to_save_dir


class PreviewSchema(formencode.Schema):
    allow_extra_fields = True
    title = formencode.validators.String()


class PreviewView(BaseHelper):

    navigation_actions = {'next': 'metadata', 
                          'previous': 'choose',}

    @view_config(route_name='preview', renderer='templates/preview.pt',
        http_cache=(0, {'no-store': True, 'no-cache': True, 'must-revalidate': True}))
    def generate_html_view(self):
        self.check_login()
        
        request = self.request
        session = request.session
        module = request.params.get('module')
        if module:
            conn = sword2cnx.Connection(session['service_document_url'],
                                        user_name=session['username'],
                                        user_pass=session['password'],
                                        always_authenticate=True,
                                        download_service_document=False)

            parts = urlparse.urlsplit(module)
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
            
        defaults = {}
        defaults['title'] = request.session.get('title', '')
        form = Form(request,
                    schema=PreviewSchema,
                    defaults=defaults
                   )

        body_filename = request.session.get('preview-no-cache')
        if body_filename is None:
            body_filename = 'index.xhtml'
        else:
            del request.session['preview-no-cache']

        return {
            'body_base': '%s%s/' % (
                         request.static_url('oerpub.rhaptoslabs.swordpushweb:transforms/'),
                         request.session['upload_dir']),
            'body_url': '%s%s/index.html'% (
                         request.static_url('oerpub.rhaptoslabs.swordpushweb:transforms/'),
                         request.session['upload_dir']),
            'form': FormRenderer(form),
            'editor': EditorHelper(request)
        }

    @reify
    def neworexisting_dialog(self):
        return self.macro_renderer.implementation().macros['neworexisting_dialog']

    def get_NextButtonToolTip(self):
      source = self.get_source()
      if source == 'newemptymodule':
          return 'Add module description and save module to cnx.org'
      elif source == 'existingmodule':
          return 'Review module description and save module to cnx.org'
      else:
          return 'Select whether this will be used for a new module or to override the contents of an existing module'

