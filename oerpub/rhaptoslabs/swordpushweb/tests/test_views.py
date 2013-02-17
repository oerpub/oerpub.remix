import os

import unittest

from pyramid import testing

from oerpub.rhaptoslabs.swordpushweb.views.metadata import Metadata_View

WORKING_DIR = os.getcwd()

SESSION_DATA = \
        {'username': '',
         'password': '',
         'service_document_url': '',
         'collections': [],
        }

CONFIG_FILE_PATH = \
    os.path.join(WORKING_DIR,
                 '..',
                 '..',
                 'src',
                 'oerpub.rhaptoslabs.swordpushweb',
                 'oerpub',
                 'rhaptoslabs',
                 'swordpushweb',
                 'config')
REGISTRY_DATA = \
        {'config_file': CONFIG_FILE_PATH,
        }

class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_my_view(self):
        request = testing.DummyRequest()
        self.prepEnvironment(request)

        view = Metadata_View(request)
        content = view.generate_html_view()
        #self.assertEqual(info['project'], 'SwordPush')

    def prepEnvironment(self, request):
        for k, v in SESSION_DATA.items():
            request.session[k] = v

        for k, v in REGISTRY_DATA.items():
            request.registry.settings[k] = v

