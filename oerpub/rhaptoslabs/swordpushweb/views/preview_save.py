import os
import json
from lxml import etree

from pyramid.view import view_config
from pyramid.response import Response

from rhaptos.cnxmlutils.utils import aloha_to_etree, etree_to_valid_cnxml

from choose import validate_cnxml
from oerpub.rhaptoslabs.swordpushweb.views.utils import (
    save_and_backup_file,
    save_zip,
    ConversionError)
from utils import check_login, get_files_from_zipfile

@view_config(route_name='preview_save')
def preview_save(request):
    check_login(request)
    html = request.POST['html']
    if isinstance(html, unicode):
        html = html.encode('ascii', 'xmlcharrefreplace')        

    save_dir = os.path.join(request.registry.settings['transform_dir'],
        request.session['upload_dir'])
    # Save new html file from preview area
    save_and_backup_file(save_dir, 'index.html', html)

    conversionerror = ''

    # Get the title from aloha html. We have to do this using a separate
    # parse operation, because aloha_to_etree below does not give us a
    # tree on which path() works. A bug or this developer is just stumped.
    tree = etree.fromstring(html, etree.HTMLParser())
    try:
        edited_title = tree.xpath('/html/head/title/text()')[0]
        request.session['title'] = edited_title
    except IndexError:
        if not request.session.get('title', None):
            request.session['title'] = 'Untitled Document'

    #transform preview html to cnxml
    cnxml = None
    try:
        tree = aloha_to_etree(html)           #1 create structured HTML5 tree
        cnxml = etree_to_valid_cnxml(tree, pretty_print=True)
    except Exception as e:
        #return render_conversionerror(request, str(e))
        conversionerror = str(e)

    if cnxml is not None:
        save_and_backup_file(save_dir, 'index.cnxml', cnxml)
        files = get_files_from_zipfile(os.path.join(save_dir, 'upload.zip'))
        save_zip(save_dir, cnxml, html, files)
        try:
            validate_cnxml(cnxml)
        except ConversionError as e:
            #return render_conversionerror(request, str(e))
            conversionerror = str(e)

    response = Response(json.dumps({'saved': True, 'error': conversionerror}))
    response.content_type = 'application/json'
    return response

