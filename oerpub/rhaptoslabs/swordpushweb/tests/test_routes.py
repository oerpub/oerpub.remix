import unittest
from pyramid import testing

import oerpub.rhaptoslabs.swordpushweb as ors

ROUTES = {'admin_config':       '/config',
          'login':              '/',
          'cnxlogin':           '/cnxlogin',
          'choose':             '/choose',
          'preview':            '/preview',
          'preview_header':     '/preview_header',
          'preview_body':       '/preview_body',
          'cnxml':              '/cnxml',
          'metadata':           '/metadata',
          'summary':            '/summary',
          'logout':             '/logout',
          'module_association': '/module_association',
          'modules_list':       '/modules_list',
          'choose-module':      '/choose-module',
          }

'catchall_static'
'/preview_css/*subpath'
'oerpub.rhaptoslabs.swordpushweb.static.static_view'


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_routes(self):
        ors.add_routes(self.config)
        routes = self.config.get_routes_mapper().get_routes()
        route_names = [r.name for r in routes]
        route_paths = [r.path for r in routes]

        for name, path in ROUTES.items():
            assert name in route_names, 'Route %s not found.' % name 
            assert path in route_paths, 'Path %s not found.' % path
