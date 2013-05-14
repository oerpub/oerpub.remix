import urllib
import urlparse
import formencode
from lxml import etree

from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid_simpleform.renderers import FormRenderer
from pyramid.renderers import render_to_response

from oerpub.rhaptoslabs import sword2cnx
from oerpub.rhaptoslabs.swordpushweb.views.choose import GoogleDocProcessor
from oerpub.rhaptoslabs.swordpushweb.session import CnxSession, \
    TestingSession

from utils import load_config

TESTING = False      

class LoginSchema(formencode.Schema):
    allow_extra_fields = True
    service_document_url = formencode.validators.String(not_empty=True)
    username = formencode.validators.PlainText(not_empty=True)
    password = formencode.validators.NotEmpty()

def auth(service_document_url, username, password):
    # Get the service document and persist what's needed.
    conn = sword2cnx.Connection(service_document_url,
                                user_name=username, user_pass=password,
                                always_authenticate=True,
                                download_service_document=True)
    if not conn.sd.valid:
        # Invalid username of password.
        return None

    collections = [{'title': i.title, 'href': i.href} for i in \
        sword2cnx.get_workspaces(conn)]

    # Get needed info from the service document
    doc = etree.fromstring(conn.sd.raw_response)

    # Prep the namespaces. xpath does not like a None namespace.
    namespaces = doc.nsmap
    del namespaces[None]

    # We need some details from the service document.
    # TODO: This is fragile, since it assumes a certain structure.
    workspace_title = doc.xpath('//atom:title',
            namespaces=namespaces)[0].text
    sword_version = doc.xpath('//sword:version',
            namespaces=namespaces)[0].text
    maxuploadsize = doc.xpath('//sword:maxuploadsize',
            namespaces=namespaces)[0].text

    return CnxSession(username, password, service_document_url,
            workspace_title, sword_version, maxuploadsize, collections)

@view_config(route_name='login')
def login_view(request):
    """
    Perform a 'login' by getting the service document from a sword repository.
    """

    templatePath = 'templates/login.pt'

    config = load_config(request)
    form = Form(request, schema=LoginSchema)
    field_list = [
        ('username',),
        ('password',),
    ]

    session = request.session

    # validate the form in order to compute all errors
    valid_form = form.validate()
    request['errors'] = form.all_errors()

    # Check for successful form completion
    if 'form.submitted' in request.POST and valid_form:
        login = auth(form.data['service_document_url'], form.data['username'],
                form.data['password'])

        if login is None:
            request['errors'] = ["Invalid username or password. Please try again.",]
            response = {
                'form': FormRenderer(form),
                'field_list': field_list,
                'config': config,
            }
            return render_to_response(templatePath, response, request=request)

        # The login details are persisted on the session.
        if TESTING:
            session['login'] = TestingSession()
        else:
            session['login'] = login

        return HTTPFound(location=request.route_url('choose'))
    elif 'login' in session:
        return HTTPFound(location=request.route_url('choose'))

    # If not signed in, go to login page
    response = {
        'form': FormRenderer(form),
        'field_list': field_list,
        'config': config,
    }
    return render_to_response(templatePath, response, request=request)

@view_config(context='velruse.AuthenticationComplete')
def google_login_complete(request):
    context = request.context
    result = {
        'provider_type': context.provider_type,
        'provider_name': context.provider_name,
        'profile': context.profile,
        'credentials': context.credentials,
    }

    qs = urllib.unquote(request.params.get('state', '')[32:])
    args = dict(urlparse.parse_qsl(qs))
    docid = args.get('docid', None)

    if docid is not None:
        # Google login was done because we want to import the document
        # identified by docid. Go ahead and import it.
        processor = GoogleDocProcessor(request)
        return processor.callback(request, docid,
            context.credentials['oauthAccessToken'])

    return HTTPFound(location=request.route_url('choose'))

@view_config(context='velruse.AuthenticationDenied')
def google_login_denied(request):
    request.session.flash('OAuth2 authorization failed.')
    return HTTPFound(location=request.route_url('choose'))
