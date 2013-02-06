import os
import ConfigParser

import unittest
from webtest import TestApp

from oerpub.rhaptoslabs.swordpushweb import main


class TestWorflowStepsUtility(unittest.TestCase):
    def setUp(self):
        settings = {}
        cwd = os.getcwd()
        cwd = cwd.rstrip(os.path.join('parts', 'test'))
        cwd= os.path.join('', cwd, 'src', 'oerpub.rhaptoslabs.swordpushweb',
                          'oerpub', 'rhaptoslabs')
        path = os.path.join('..', '..', 'src',
                            'oerpub.rhaptoslabs.swordpushweb', 'oerpub', 
                            'rhaptoslabs', 'development.ini')
        config = ConfigParser.ConfigParser()
        config.read(path)
        settings = dict(config.items('app:pyramid', 0, {'here':cwd}))
        app = main({}, **settings)
        self.testapp = TestApp(app)

    def test_root(self):
        res = self.testapp.get('/', status=200)
        self.failUnless('Connexions Importer' in res.body)
