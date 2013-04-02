import formencode

from pyramid.decorator import reify
from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid.renderers import get_renderer
from pyramid_simpleform.renderers import FormRenderer
from oerpub.rhaptoslabs.cnxml2htmlpreview.cnxml2htmlpreview import cnxml_to_htmlpreview

from helpers import BaseHelper 
from ..editor import EditorHelper
from oerpub.rhaptoslabs.swordpushweb.views.utils import (
    save_and_backup_file,
    save_zip,
    ConversionError)


class PreviewSchema(formencode.Schema):
    allow_extra_fields = True
    title = formencode.validators.String()


class PreviewView(BaseHelper):
    
    def __init__(self, request):
        super(PreviewView, self).__init__(request)
        self.bootstrap_macro_renderer = get_renderer("templates/bootstrap_macros.pt")
    
    @view_config(route_name='preview', renderer='templates/preview.pt',
        http_cache=(0, {'no-store': True, 'no-cache': True, 'must-revalidate': True}))
    def process(self):
        super(PreviewView, self)._process()
        self.do_transition()
        return self.navigate()

    def do_transition(self, form=None):
        request = self.request
        session = request.session
        body_filename = session.get('preview-no-cache')
        if body_filename is None:
            body_filename = 'index.xhtml'
    
    def navigate(self, errors=None, form=None):
        # See if this was a plain navigation attempt
        view = super(PreviewView, self)._navigate(errors, form, 'workflownav.preview.submitted')
        if view:
            return view

        request = self.request
        defaults = {}
        defaults['title'] = request.session.get('title', '')
        form = Form(request,
                    schema=PreviewSchema,
                    defaults=defaults
                   )

        return {
            'body_base': '%s%s/' % (
                         request.static_url('oerpub.rhaptoslabs.swordpushweb:transforms/'),
                         request.session['upload_dir']),
            'body_url': '%s%s/index.html'% (
                         request.static_url('oerpub.rhaptoslabs.swordpushweb:transforms/'),
                         request.session['upload_dir']),
            'form': FormRenderer(form),
            'editor': EditorHelper(request),
            'view': self,
        }

    @reify
    def neworexisting_dialog(self):
        return self.bootstrap_macro_renderer.implementation().macros['neworexisting_dialog']

    @reify
    def back_step_label(self):
        return "&laquo; Back: Return to start page"
    
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
        elif source == 'importmodule':
              return 'Select whether this will be used for a new module or to override the contents of an existing module'
        return 'Select whether this will be used for a new module or to override the contents of an existing module'

    @reify
    def back_step_title(self):
        return "Return to the initial page"
        
    @reify
    def get_new_module_destination(self):
        # where does the New Module button from the New or Existing Module
        # dialog box take you?
        source = self.session['source']
        if source == 'new' or source == 'existingmodule':
            # the New or Existing Module dialog box will not be shown
            return 'preview'
        else:
	   return super(PreviewView, self).get_next_action(target='new')

    @reify
    def get_existing_module_destination(self):
        # where does the New Module button from the New or Existing Module
        # dialog box take you?
        source = self.session['source']
        if source == 'new' or source == 'existingmodule':
            # the New or Existing Module dialog box will not be shown
            return 'preview'
        else:
	   return super(PreviewView, self).get_next_action(target='existingmodule')
