What this is
============

The sword push web client is a Pyramid webapp designed to let a user upload a MS Word or OpenOffice document, do a conversion to CNXML, and push it to the cnx.org site as a module, using the sword v1 or v2 interface. It will be generalised to enable pushing to any sword-compliant service.

Quick Start
===========

This will probably end up being buildout-enabled. Until that happens, the following should get you going on an Ubuntu based system::

    git clone git@github.com:jbeyers/oerpub.rhaptoslabs.swordpushweb.git swordpushweb
    cd swordpushweb/
    virtualenv --no-site-packages .
    ./bin/easy_install pyramid
    ./bin/python setup.py develop
    ./bin/paster serve development.ini 
