import os
import datetime

from pyramid.response import Response
from pyramid.view import view_config

from utils import check_login

@view_config(route_name='download_zip',
    http_cache=(0, {'no-store': True, 'no-cache': True, 'must-revalidate': True}))
def download_zip(request):
    check_login(request)

    res = Response(content_type='application/zip')
    res.headers.add('Content-Disposition', 'attachment;filename=saved-module.zip')

    save_dir = os.path.join(request.registry.settings['transform_dir'],
        request.session['upload_dir'])
    zipfile = open(os.path.join(save_dir, 'upload.zip'), 'rb')
    stat = os.fstat(zipfile.fileno())
    res.app_iter = iter(lambda: zipfile.read(4096), '')
    res.content_length = stat.st_size
    res.last_modified = datetime.datetime.utcfromtimestamp(
        stat.st_mtime).strftime('%a, %d %b %Y %H:%M:%S GMT')
    return res
