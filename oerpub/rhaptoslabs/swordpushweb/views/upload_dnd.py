import os
import re
import json
import datetime
import mimetypes

from pyramid.view import view_config
from pyramid.response import Response

from oerpub.rhaptoslabs.swordpushweb.views.utils import check_login


@view_config(route_name='upload_dnd')
def upload_dnd(request):
    check_login(request)

    session = request.session['login']
    save_dir = session.saveDir

    # userfn, if browser does not support naming of blobs, this might be
    # 'blob', so we need to further uniquefy it.
    userfn = request.POST['upload'].filename or ''
    ext = ''
    mtype = request.POST['upload'].headers.get('content-type')
    if mtype is not None:
        ext = mimetypes.guess_extension(mtype) or ''

    # If it has an extension (a dot and three of four characters at the end),
    # strip it
    userfn = re.compile('\.\w{3,4}$').sub('', userfn)
    fn = userfn + '_' + datetime.datetime.now().strftime('%s') + ext

    # Store upload
    blk = request.POST['upload'].file.read()
    session.addFile(fn, blk)

    response = Response(json.dumps({'url': fn}))
    response.content_type = 'application/json'
    return response
