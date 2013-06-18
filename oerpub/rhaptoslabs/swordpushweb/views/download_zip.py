import os
import datetime
import shutil

from pyramid.response import Response
from pyramid.view import view_config

from utils import check_login

@view_config(route_name='download_zip',
    http_cache=(0, {'no-store': True, 'no-cache': True, 'must-revalidate': True}))
def download_zip(request):
    check_login(request)

    res = Response(content_type='application/zip')
    res.headers.add('Content-Disposition', 'attachment;filename=saved-module.zip')

    previous_upload_dir = request.session.get('previous_save_dir', None)
    if previous_upload_dir is not None:
        del(request.session['previous_save_dir'])

    login = request.session['login']
    save_dir = login.hasData and login.saveDir or previous_upload_dir
    assert save_dir is not None

    zipfile = open(os.path.join(save_dir, 'upload.zip'), 'rb')
    stat = os.fstat(zipfile.fileno())
    res.app_iter = iter(lambda: zipfile.read(4096), '')
    res.content_length = stat.st_size
    res.last_modified = datetime.datetime.utcfromtimestamp(
        stat.st_mtime).strftime('%a, %d %b %Y %H:%M:%S GMT')

    # If there is a previous_upload_dir, kill it. This allows the user
    # one final chance to download it even if the rest of the session has been
    # killed. It is okay to delete the upload.zip file, as we still have it
    # open and unix will delete it on the last close().
    if previous_upload_dir is not None:
        try:
            shutil.rmtree(previous_upload_dir, ignore_errors=True)
        except OSError:
            pass
    return res
