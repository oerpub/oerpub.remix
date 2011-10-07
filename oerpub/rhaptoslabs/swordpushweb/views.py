import os
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
    """
    Perform a 'login' by getting the service document from a sword repository.
    """
    # TODO: check credentials against Connexions and ask for login
    # again if failed.

    defaults = {'service_document_url': 'http://cnx.org/sword'}
    form = Form(request,
                schema=LoginSchema,
                defaults=defaults
                )
    field_tuples = [('service_document_url', 'Service Document URL'),
                    ('username', 'User Name'),
                    ('password', 'Password'),
                    ]

    # Check for successful form completion
    if 'form.submitted' in request.POST and form.validate():

        # The login details are persisted on the session
        session = request.session
        for field_name in [i[0] for i in field_tuples]:
            session[field_name] = form.data[field_name]

        # Get the service document and persist what's needed.
        conn = swordcnx.Connection(session['service_document_url'],
                                   user_name=session['username'],
                                   user_pass=session['password'],
                                   download_service_document=True)

        # Get available collections from SWORD service document
        # TODO: This is fragile and needs more checking
        session['collections'] = swordcnx.parse_service_document(conn.sd)
        session['current_collection'] = session['collections'][0]['url']

        # Go to the upload page
        return HTTPFound(location="/upload")
    return {
        'form': FormRenderer(form),
        'field_list': field_tuples,
        }

@view_config(route_name='logout', renderer='templates/login.pt')
def logout_view(request):
    session = request.session
    session.invalidate()
    raise HTTPFound(location='/')

class MetadataSchema(formencode.Schema):
    allow_extra_fields = True
    service_document_url = formencode.validators.String(not_empty=True)
    username = formencode.validators.PlainText(not_empty=True)
    password = formencode.validators.PlainText(not_empty=True)
    title = formencode.validators.PlainText(not_empty=True)
    keep_title = formencode.validators.Bool()
    summary = formencode.validators.PlainText(not_empty=True)
    keep_summary = formencode.validators.Bool()
    keywords = formencode.validators.PlainText(not_empty=True)
    keep_keywords = formencode.validators.Bool()
    language = formencode.validators.PlainText(not_empty=True)

@view_config(route_name='metadata', renderer='templates/metadata.pt')
def metadata_view(request):
    """
    Handle metadata adding and uploads
    """

    defaults = {'service_document_url': 'http://cnx.org/sword'}
    form = Form(request,
                schema=MetadataSchema,
                defaults=defaults
                )


    # Check for successful form completion
    if 'form.submitted' in request.POST and form.validate():

        # Parse form elements
        filesToUpload = {}
        for key in ['file1','file2','file3']:
            if hasattr(form.data[key], 'file'):
                filesToUpload[os.path.basename(form.data[key].filename)] = \
                    form.data[key].file

        session = request.session
        # Send zip file to Connexions through SWORD interface
        conn = swordcnx.Connection(form.data['url'],
                                   user_name=session['username'],
                                   user_pass=session['password'],
                                   download_service_document=False)

        response = swordcnx.upload_multipart(conn,
                                             form.data['title'],
                                             form.data['summary'],
                                             form.data['language'],
                                             form.data['keywords'].split("\n"),
                                             filesToUpload)


        # Go to the upload page
        return HTTPFound(location="/summary")
    return {
        'form': FormRenderer(form),
        }

