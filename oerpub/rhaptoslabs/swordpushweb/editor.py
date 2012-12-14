from pkg_resources import resource_filename
from pyramid.renderers import get_renderer
from pyramid.chameleon_zpt import renderer_factory
from translationstring import ChameleonTranslate
from chameleon.zpt.loader import TemplateLoader

# This template loader implementation shamelessly stolen from deform
class TemplateError(Exception):
    pass

class ZPTTemplateLoader(TemplateLoader):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('encoding', 'utf-8')
        super(ZPTTemplateLoader, self).__init__(*args, **kwargs)

    def load(self, filename, *args, **kwargs):
        try:
            return super(ZPTTemplateLoader, self).load(
                filename, *args, **kwargs)
        except ValueError:
            raise TemplateError(filename)

class ZPTRendererFactory(object):
    def __init__(self, search_path, auto_reload=True, debug=False,
                 encoding='utf-8', translator=None):
        loader = ZPTTemplateLoader(search_path=search_path,
                                   auto_reload=auto_reload,
                                   debug=debug,
                                   encoding=encoding,
                                   translate=ChameleonTranslate(translator))
        self.loader = loader

    def __call__(self, template_name, **kw):
        return self.load(template_name)(**kw)

    def load(self, template_name):
        return self.loader.load(template_name + '.html')

class EditorHelper(object):
    def __init__(self, request):
        search_path = request.registry.settings['aloha.editor']
        renderer = ZPTRendererFactory((search_path, ), auto_reload=False)
        self.macros = renderer.load('index').macros

    def __getattr__(self, attr):
        try:
            return self.macros[attr]
        except KeyError:
            raise AttributeError(attr)

# from oerpub.rhaptoslabs.swordpushweb.editor import EditorHelper
# EditorHelper(request)
