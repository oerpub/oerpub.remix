from pyramid.decorator import reify
from pyramid.view import view_config

from module_association import Module_Association_View


class Choose_Module(Module_Association_View):

    @view_config(
        route_name='choose-module', renderer="templates/choose_module.pt")
    def process(self):
        return super(Choose_Module, self).process()

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
            return "Select a module below and then click 'Next' to start editing it"
        elif source == 'importmodule':
              return 'Select whether this will be used for a new module or to override the contents of an existing module'
        return 'Select whether this will be used for a new module or to override the contents of an existing module'

    @reify
    def back_step_title(self):
        return "Return to the initial page"
