import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'PasteScript',
    'pyramid',
    'pyramid_debugtoolbar',
    'pyramid_simpleform',
    'cryptacular',
    'pyramid_beaker',
    'pycrypto==2.5',
    'Markdown',
    'BeautifulSoup==3.2.1',
    'MySQL-python==1.2.4',
    'peppercorn',
    'z3c.batching',

    ]

tests_requires = requires.extend(
    ['gdata',
     'libxml2-python',
     'oerpub.rhaptoslabs.sword2cnx',
     'oerpub.rhaptoslabs.latex2cnxml',
     'oerpub.rhaptoslabs.html_gdocs2cnxml',
     'oerpub.rhaptoslabs.cnxml2htmlpreview',
    ]
)

setup(name='oerpub.rhaptoslabs.swordpushweb',
      version='0.1.4',
      description='SwordPush',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=tests_requires,
      test_suite="swordpush",
      entry_points = """\
      [paste.app_factory]
      main = oerpub.rhaptoslabs.swordpushweb:main
      """,
      paster_plugins=['pyramid'],
      )

