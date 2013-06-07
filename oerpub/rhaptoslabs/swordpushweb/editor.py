import re
from translationstring import ChameleonTranslate
from chameleon.loader import TemplateLoader
from chameleon.zpt.template import PageTemplateFile as BasePageTemplateFile

COMMENTRE = re.compile('<!--(/?metal:.*?)-->')

class TemplateError(Exception):
    pass

class PageTemplateFile(BasePageTemplateFile):
    """ Extend the Base PageTemplateFile and change the cook method
        to add a bit of comment trickery, I need to use metal tags in html
        in a way that will not confuse a browser, but will still be properly
        executed by chameleon. Doing it this way, we can use html comments
        to hide metal. """
    def cook(self, body):
        # Translate <!--metal: to <metal:
        b = COMMENTRE.sub(r'<\1>', body)
        return super(PageTemplateFile, self).cook(b)

class ZPTTemplateLoader(TemplateLoader):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('encoding', 'utf-8')
        super(ZPTTemplateLoader, self).__init__(*args, **kwargs)

    def load(self, filename, *args, **kwargs):
        try:
            return super(ZPTTemplateLoader, self).load(
                filename, PageTemplateFile, *args, **kwargs)
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
