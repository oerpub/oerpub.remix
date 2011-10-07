import os
import base64
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

import formencode

from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer

from languages import languages
import oerpub.rhaptoslabs.sword1cnx as swordcnx

class LoginSchema(formencode.Schema):
    allow_extra_fields = True
    service_document_url = formencode.validators.String(not_empty=True)
    username = formencode.validators.PlainText(not_empty=True)
    password = formencode.validators.PlainText(not_empty=True)

@view_config(route_name='main', renderer='templates/login.pt')
def login_view(request):
    defaults = {'service_document_url': 'http://cnx.org/sword'}
    form = Form(request,
                schema=LoginSchema,
                defaults=defaults
                )
    field_tuples = [('service_document_url', 'Service Document URL'),
                    ('username', 'User Name'),
                    ('password', 'Password'),
                    ]
    if 'form.submitted' in request.POST and form.validate():
        session = request.session
        for field_name in [i[0] for i in field_tuples]:
            session[field_name] = form.data[field_name]
        return HTTPFound(location="/auth")
    return {
        'form': FormRenderer(form),
        'field_list': field_tuples,
        }

@view_config(route_name='logout', renderer='templates/login.pt')
def logout_view(request):
    session = request.session
    session.invalidate()
    raise HTTPFound(location='/')

@view_config(route_name='auth', renderer='templates/upload.pt')
def auth_view(request):
    """
    Handle authentication (login) requests.
    """
    # TODO: check credentials against Connexions and ask for login
    # again if failed.

    session = request.session
    serviceDocument = session['service_document_url']

    # Encode authentication information
    username = session['username']
    password = session['password']

    # Authenticate to Connexions
    conn = swordcnx.Connection(serviceDocument,
                               user_name=username,
                               user_pass=password,
                               download_service_document=True)

    # Get available collections from SWORD service document
    swordCollections = swordcnx.parse_service_document(conn.sd)


    return {
        'serviceDocument': serviceDocument,
        'swordCollections': swordCollections,
        'url': '',
        'title': '',
        'keepTitle': False,
        'summary': '',
        'keepSummary': False,
        'keywords': '',
        'keepKeywords': True,
        'languages': languages,
        'language': 'en',
    }

@view_config(route_name='upload', renderer='templates/upload.pt')
def upload_view(request):
    """
    Handle SWORD uploads POSTed from a form.
    """

    inputs = request.params

    # Decode authentication information
    authString = base64.b64decode(inputs['credentials'])
    pos = authString.find(':')
    username = authString[:pos]
    password = authString[pos+1:]
    assert base64.b64encode(username + ':' + password) == inputs['credentials']

    conn = swordcnx.Connection(inputs['serviceDocument'],
                               user_name=username,
                               user_pass=password,
                               download_service_document=True)

    # Get available collections from SWORD service document
    swordCollections = swordcnx.parse_service_document(conn.sd)

    # Parse form elements
    filesToUpload = {}
    for key in ['file1','file2','file3']:
        if hasattr(inputs[key], 'file'):
            filesToUpload[os.path.basename(inputs[key].filename)] = \
                inputs[key].file

    # Send zip file to Connexions through SWORD interface
    conn = swordcnx.Connection(inputs['url'],
                               user_name=username,
                               user_pass=password,
                               download_service_document=False)

    response = swordcnx.upload_multipart(conn,
                                         inputs['title'],
                                         inputs['summary'],
                                         inputs['language'],
                                         inputs['keywords'].split("\n"),
                                         filesToUpload)

    return {
        'serviceDocument': inputs['serviceDocument'],
        'credentials': inputs['credentials'],
        'swordCollections': swordCollections,
        'url': inputs['url'],
        'title': inputs['title'] if inputs.get('keepTitle') else '',
        'keepTitle': inputs.get('keepTitle', False),
        'summary': inputs['summary'] if inputs.get('keepSummary') else '',
        'keepSummary': inputs.get('keepSummary', False),
        'keywords': inputs['keywords'] if inputs.get('keepKeywords') else '',
        'keepKeywords': inputs.get('keepKeywords', False),
        'languages': languages,
        'language': inputs['language'],
    }
