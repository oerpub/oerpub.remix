
Getting OpenOffice set up:
==========================

Install headless version::

  apt-get install openoffice.org-headless openoffice.org-writer openoffice.org-draw

Create macro. You need to do this as the user that will be running the
sword services -- probably the web server or whoever is running
paster. Replace the Module1 macro::

  cp Module1.xba ~/.openoffice.org/3/user/basic/Standard/.


The rest:
=========

Packages to install::

  apt-get install libxslt-dev libxml2-dev python-dev python-libxml2 python-libxslt1

To get the app going::

    virtualenv --no-site-packages .

    git clone git://github.com/rochecompaan/rhaptos.cnxmlutils.git
    cd rhaptos.cnxmlutils
    ../bin/python setup.py build
    ../bin/python setup.py install
    cd ..

    echo "Copy sword2 library source manually for now."
    read -p "Press Enter to continue."
    cd sword2
    ../bin/python setup.py build
    ../bin/python setup.py install
    cd ..

    git clone git://github.com/cscheffler/oerpub.rhaptoslabs.sword2cnx.git
    cd oerpub.rhaptoslabs.sword2cnx
    ../bin/python setup.py build
    ../bin/python setup.py install
    cd ..

    git clone git://github.com/cscheffler/oerpub.rhaptoslabs.sword2cli.git

    git clone git://github.com/therealmarv/oerpub.rhaptoslabs.cnxml2htmlpreview.git
