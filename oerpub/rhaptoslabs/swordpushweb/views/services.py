import os
import datetime
import shutil
#debug only 
import json

from pyramid.response import Response
from pyramid.view import view_config

from oerpub.rhaptoslabs.swordpushweb.session import (
    AnonymousSession,)
from oerpub.rhaptoslabs.swordpushweb.views.utils import (
    create_save_dir,)
from utils import (
    check_login,)

# https://pyramid.readthedocs.org/en/latest/narr/renderers.html#jsonp-renderer
# pyramid.renderers.JSONP is a JSONP renderer factory helper which implements a hybrid json/jsonp renderer. JSONP is useful for making cross-domain AJAX requests.

@view_config(route_name='gdoc2html', renderer="json")
def gdoc2html(request):
    session = request.session
    import pdb; pdb.set_trace();

    # grab inputs
    if 'html' in request.POST: 
      html = request.POST['html'] 
    elif 'html' in request.GET: 
      html = request.GET['html']
    else:
      return

    if 'textbook_html' in request.POST:
      textbook_html = request.POST['textbook_html'] is '1'
    elif 'textbook_html' in request.GET:
      textbook_html = request.GET['textbook_html'] is '1'
    else:
      textbook_html = True

    if 'copy_images' in request.POST:
      copy_images = request.POST['copy_images'] is '1'
    elif 'copy_images' in request.GET:
      copy_images = request.GET['copy_images'] is '1'
    else:
      copy_images = False

    # be anonymous
    session['login'] = AnonymousSession()

    # setup work driectory: save_dir = transform_dir + user_subdir_name
    transform_dir = request.registry.settings['transform_dir']
    user_subdir_name, save_dir = create_save_dir(request)

    # setup response that will be returned
    #res = Response(content_type='text/html')
    #res.headers.add('Content-Disposition', 'attachment;filename=gdoc_transform.html')
    #res.text = html
    #res.content_length = len(html)
    # res.last_modified = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    #res.last_modified = datetime.datetime.utcfromtimestamp(
    #    datetime.datetime.now()).strftime('%a, %d %b %Y %H:%M:%S GMT')
    #res.last_modified = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')

    jsonresult =  { "html": html, "aloha-ready": True }
    #return jsonresult
    return Response('OK')
