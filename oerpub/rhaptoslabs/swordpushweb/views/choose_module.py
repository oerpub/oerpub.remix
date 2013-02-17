from pyramid.decorator import reify
from pyramid.view import view_config

from module_association import Module_Association_View


class Choose_Module(Module_Association_View):

    # NOTE: Your implementation class *must* define these actions if you want
    # to reuse the navigation and batch macros.
    navigation_actions = {'next': 'preview', 
                          'previous': 'choose',
                          'batch': 'choose-module'}

    @view_config(
        route_name='choose-module', renderer="templates/choose_module.pt")
    def generate_html_view(self):
        return super(Choose_Module, self).generate_html_view()

    @reify
    def content_macro(self):
        return self.macro_renderer.implementation().macros['content_macro']


