import os
import datetime
import shutil
#debug only 
import json

from pyramid.response import Response
from pyramid.view import view_config

from oerpub.rhaptoslabs.swordpushweb.session import (
    AnonymousSession,)

from oerpub.rhaptoslabs.html_gdocs2cnxml.gdocs2cnxml import (
    gdocs_to_cnxml,)

from oerpub.rhaptoslabs.swordpushweb.views.utils import (
    create_save_dir, 
    clean_cnxml, 
    update_html,)

@view_config(route_name='gdoc2html', renderer="json")
def gdoc2html(request):
    session = request.session

    # grab inputs
    if 'html' in request.POST: 
      html = request.POST['html'] 
    else:
      return

    if 'textbook_html' in request.POST:
      textbook_html = request.POST['textbook_html'] is '1'
    else:
      textbook_html = True

    if 'copy_images' in request.POST:
      copy_images = request.POST['copy_images'] is '1'
    else:
      copy_images = False

    # be anonymous
    session['login'] = AnonymousSession()

    # setup work driectory: save_dir = transform_dir + user_subdir_name
    transform_dir = request.registry.settings['transform_dir']
    user_subdir_name, save_dir = create_save_dir(request)

    # allow cross domain access
    request.response.headers.add('Access-Control-Allow-Origin', '*')
    
    # convert gdoc html to cnxml to textbook (aka strcutured) html or aloha-ready html
    cnxml, objects = gdocs_to_cnxml(html, bDownloadImages=copy_images)
    cnxml = clean_cnxml(cnxml)
    title = None
    metadata = None
    alohareadyhtml, structuredhtml, conversion_error = update_html(cnxml, title, metadata)
    if conversion_error is None:
      if textbook_html:
        html = structuredhtml
      else:
        html = alohareadyhtml
    else:
      html = ""

    jsonresult =  { "html": html, 
                    "textbook_html": textbook_html,
                    "copy_images": copy_images, }
    return jsonresult
