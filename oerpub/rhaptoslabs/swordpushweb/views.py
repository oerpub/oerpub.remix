import os
import types
import shutil
import datetime
import zipfile
import traceback
import json
import logging
import libxml2
import lxml
import re
import subprocess
import urlparse

from cStringIO import StringIO
import peppercorn
from lxml import etree
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render_to_response, get_renderer
from pyramid.response import Response
from pyramid.decorator import reify

import formencode

from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer

from languages import languages
from oerpub.rhaptoslabs import sword2cnx
from rhaptos.cnxmlutils.odt2cnxml import transform
from rhaptos.cnxmlutils.validatecnxml import validate
from oerpub.rhaptoslabs.cnxml2htmlpreview.cnxml2htmlpreview import cnxml_to_htmlpreview
from oerpub.rhaptoslabs.cnxml2htmlpreview.html2cnxml import html_to_cnxml
import gdata.gauth
import gdata.docs.client
from oerpub.rhaptoslabs.html_gdocs2cnxml.gdocs_authentication import getAuthorizedGoogleDocsClient
from oerpub.rhaptoslabs.html_gdocs2cnxml.gdocs2cnxml import gdocs_to_cnxml
import urllib2
from oerpub.rhaptoslabs.html_gdocs2cnxml.htmlsoup2cnxml import htmlsoup_to_cnxml, aloha_htmlsoup_to_cnxml
from oerpub.rhaptoslabs.latex2cnxml.latex2cnxml import latex_to_cnxml
from utils import escape_system, clean_cnxml, load_config
from utils import save_config, add_directory_to_zip
from utils import get_cnxml_from_zipfile, add_featuredlinks_to_cnxml
from utils import get_files_from_zipfile, build_featured_links
from utils import create_module_in_2_steps
import convert as JOD # Imports JOD convert script
import jod_check #Imports script which checks to see if JOD is running
from z3c.batching.batch import Batch

from utils import check_login, get_metadata_from_repo, extract_to_save_dir
from utils import ZIP_PACKAGING, get_files
from helpers import BaseHelper 
import parse_sword_treatment

TESTING = False      
CWD = os.getcwd()


class LoginSchema(formencode.Schema):
    allow_extra_fields = True
    service_document_url = formencode.validators.String(not_empty=True)
    username = formencode.validators.PlainText(not_empty=True)
    password = formencode.validators.NotEmpty()

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
        # The login details are persisted on the session
        for field_name in [i[0] for i in field_list]:
            session[field_name] = form.data[field_name]
        session['service_document_url'] = form.data['service_document_url']
        loggedIn = True
    # Check if user is already authenticated
    else:
        loggedIn = True
        for key in ['username', 'password', 'service_document_url', 'collections', 'workspace_title', 'sword_version', 'maxuploadsize']:
            if not session.has_key(key):
                loggedIn = False
        if loggedIn:
            return HTTPFound(location=request.route_url('choose'))

    # TODO: check credentials against Connexions and ask for login
    # again if failed.

    # If not signed in, go to login page
    if not loggedIn:
        response = {
            'form': FormRenderer(form),
            'field_list': field_list,
            'config': config,
        }
        return render_to_response(templatePath, response, request=request)

    # Here we know that the user is authenticated and that they did so
    # by logging in (rather than having had a cookie set already)
    if TESTING:
        session['workspace_title'] = "Connexions"
        session['sword_version'] = "2.0"
        session['maxuploadsize'] = "60000"
        session['collections'] = [{'title': 'Personal Workspace', 'href': 'http://'}]
    else:
        # Get the service document and persist what's needed.
        conn = sword2cnx.Connection(session['service_document_url'],
                                    user_name=session['username'],
                                    user_pass=session['password'],
                                    always_authenticate=True,
                                    download_service_document=True)
        try:
            # Get available collections from SWORD service document
            # We create a list of dictionaries, otherwise we'll have problems
            # pickling them.
            if not conn.sd.valid:
                raise Exception
            session['collections'] = [{'title': i.title, 'href': i.href}
                                      for i in sword2cnx.get_workspaces(conn)]
        except:
            del session['username']
            del session['password']
            request['errors'] = ["Invalid username or password. Please try again.",]
            response = {
                'form': FormRenderer(form),
                'field_list': field_list,
                'config': config,
            }
            return render_to_response(templatePath, response, request=request)

        # Get needed info from the service document
        doc = etree.fromstring(conn.sd.raw_response)

        # Prep the namespaces. xpath does not like a None namespace.
        namespaces = doc.nsmap
        del namespaces[None]

        # We need some details from the service document.
        # TODO: This is fragile, since it assumes a certain structure.
        session['workspace_title'] = doc.xpath('//atom:title',
                                               namespaces=namespaces
                                               )[0].text
        session['sword_version'] = doc.xpath('//sword:version',
                                             namespaces=namespaces
                                             )[0].text
        session['maxuploadsize'] = doc.xpath('//sword:maxuploadsize',
                                             namespaces=namespaces
                                             )[0].text

    # Go to the upload page
    return HTTPFound(location=request.route_url('choose'))


@view_config(route_name='cnxlogin')
def cnxlogin_view(request):
    check_login(request)

    config = load_config(request)
    login_url = config['login_url']

    templatePath = 'templates/cnxlogin.pt'
    response = {
        'username': request.session['username'],
        'password': request.session['password'],
        'login_url': login_url,
    }
    return render_to_response(templatePath, response, request=request)


@view_config(route_name='logout', renderer='templates/login.pt')
def logout_view(request):
    session = request.session
    session.invalidate()
    raise HTTPFound(location=request.route_url('login'))


class ConversionError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

def save_and_backup_file(save_dir, filename, content, mode='w'):
    """ save a file, but first make a backup if the file exists
    """
    if isinstance(content, unicode):
        content = content.encode('ascii', 'xmlcharrefreplace')
    filename = os.path.join(save_dir, filename)
    if os.path.exists(filename):
        os.rename(filename, filename + '~')
    f = open(filename, mode)
    f.write(content)
    f.close()

def append_zip(zipfilename, filename, content):
    """ Append files to a zip file. files is a list of tuples where each tuple
        is a (filename, content) pair. """
    zip_archive = zipfile.ZipFile(zipfilename, 'a')
    zip_archive.writestr(filename, content)
    zip_archive.close()

def save_zip(save_dir, cnxml, html, files):
    ram = StringIO()
    zip_archive = zipfile.ZipFile(ram, 'w')
    zip_archive.writestr('index.cnxml', cnxml)
    if html is not None:
        zip_archive.writestr('index.html', html)
    for filename, fileObj in files:
        zip_archive.writestr(filename, fileObj)
    zip_archive.close()
    zip_filename = os.path.join(save_dir, 'upload.zip')
    save_and_backup_file(save_dir, zip_filename, ram.getvalue(), mode='wb')

def save_cnxml(save_dir, cnxml, files):
    # write CNXML output
    save_and_backup_file(save_dir, 'index.cnxml', cnxml)

    # write files
    for filename, content in files:
        filename = os.path.join(save_dir, filename)
        f = open(filename, 'wb') # write binary, important!
        f.write(content)
        f.close()

    # we generate the preview and save the error
    conversionerror = None
    try:
        htmlpreview = cnxml_to_htmlpreview(cnxml)
    except libxml2.parserError:
        conversionerror = traceback.format_exc()

    # Zip up all the files. This is done now, since we have all the files
    # available, and it also allows us to post a simple download link.
    # Note that we cannot use zipfile as context manager, as that is only
    # available from python 2.7
    # TODO: Do a filesize check xxxx
    if conversionerror is None:
        save_and_backup_file(save_dir, 'index.html', htmlpreview)
        save_zip(save_dir, cnxml, htmlpreview, files)
    else:
        save_zip(save_dir, cnxml, None, files)
        raise ConversionError(conversionerror)

def validate_cnxml(cnxml):
    valid, log = validate(cnxml, validator="jing")
    if not valid:
        raise ConversionError(log)

def render_conversionerror(request, error):
    templatePath = 'templates/conv_error.pt'
    fname='gdoc'
    if 'filename' in request.session:
        fname=request.session['filename']
    response = {'filename' : fname, 'error': error}

    # put the error on the session for retrieval on the editor
    # view
    request.session['transformerror'] = error

    if('title' in request.session):
        del request.session['title']
    return render_to_response(templatePath, response, request=request)


class PreviewSchema(formencode.Schema):
    allow_extra_fields = True
    title = formencode.validators.String()


class PreviewView(BaseHelper):

    navigation_actions = {'next': 'metadata', 
                          'previous': 'choose',}

    @view_config(route_name='preview', renderer='templates/preview.pt',
        http_cache=(0, {'no-store': True, 'no-cache': True, 'must-revalidate': True}))
    def generate_html_view(self):
        self.check_login()
        
        request = self.request
        session = request.session
        module = request.params.get('module')
        if module:
            conn = sword2cnx.Connection(session['service_document_url'],
                                        user_name=session['username'],
                                        user_pass=session['password'],
                                        always_authenticate=True,
                                        download_service_document=False)

            parts = urlparse.urlsplit(module)
            path = parts.path.split('/')
            path = path[:path.index('sword')]
            module_url = '%s://%s%s' % (parts.scheme, parts.netloc, '/'.join(path))

            # example: http://cnx.org/Members/user001/m17222/sword/editmedia
            zip_file = conn.get_cnx_module(module_url = module_url,
                                           packaging = 'zip')
            
            save_dir = os.path.join(request.registry.settings['transform_dir'],
                                    request.session['upload_dir'])
            extract_to_save_dir(zip_file, save_dir)

            cnxml_file = open(os.path.join(save_dir, 'index.cnxml'), 'rb')
            cnxml = cnxml_file.read()
            cnxml_file.close()
            conversionerror = None
            try:
                htmlpreview = cnxml_to_htmlpreview(cnxml)
                save_and_backup_file(save_dir, 'index.html', htmlpreview)
                files = get_files(save_dir)
                save_zip(save_dir, cnxml, htmlpreview, files)
            except libxml2.parserError:
                conversionerror = traceback.format_exc()
                raise ConversionError(conversionerror)
            
        defaults = {}
        defaults['title'] = request.session.get('title', '')
        form = Form(request,
                    schema=PreviewSchema,
                    defaults=defaults
                   )

        body_filename = request.session.get('preview-no-cache')
        if body_filename is None:
            body_filename = 'index.xhtml'
        else:
            del request.session['preview-no-cache']

        return {
            'body_base': '%s%s/' % (
                         request.static_url('oerpub.rhaptoslabs.swordpushweb:transforms/'),
                         request.session['upload_dir']),
            'body_url': '%s%s/index.html'% (
                         request.static_url('oerpub.rhaptoslabs.swordpushweb:transforms/'),
                         request.session['upload_dir']),
            'form': FormRenderer(form),
        }

    @reify
    def neworexisting_dialog(self):
        return self.macro_renderer.implementation().macros['neworexisting_dialog']


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

    #transform preview html to cnxml
    try:
        cnxml = aloha_htmlsoup_to_cnxml(html)
    except Exception as e:
        #return render_conversionerror(request, str(e))
        conversionerror = str(e)

    try:
        validate_cnxml(cnxml)
    except ConversionError as e:
        #return render_conversionerror(request, str(e))
        conversionerror = str(e)
    else:
        save_and_backup_file(save_dir, 'index.cnxml', cnxml)
        files = get_files_from_zipfile(os.path.join(save_dir, 'upload.zip'))
        save_zip(save_dir, cnxml, html, files)

    response = Response(json.dumps({'saved': True, 'error': conversionerror}))
    response.content_type = 'application/json'
    return response


class CnxmlSchema(formencode.Schema):
    allow_extra_fields = True
    cnxml = formencode.validators.String(not_empty=True)


@view_config(route_name='cnxml', renderer='templates/cnxml_editor.pt')
def cnxml_view(request):
    check_login(request)
    form = Form(request, schema=CnxmlSchema)
    save_dir = os.path.join(request.registry.settings['transform_dir'], request.session['upload_dir'])
    cnxml_filename = os.path.join(save_dir, 'index.cnxml')
    transformerror = request.session.get('transformerror')

    # Check for successful form completion
    if 'cnxml' in request.POST and form.validate():
        cnxml = form.data['cnxml']

        # Keep sure we use the standard python ascii string and encode Unicode to xml character mappings
        if isinstance(cnxml, unicode):
            cnxml = cnxml.encode('ascii', 'xmlcharrefreplace')        

        # get the list of files from upload.zip if it exists
        files = []
        zip_filename = os.path.join(save_dir, 'upload.zip')
        if os.path.exists(zip_filename):
            zip_archive = zipfile.ZipFile(zip_filename, 'r')
            for filename in zip_archive.namelist():
                if filename == 'index.cnxml':
                    continue
                fp = zip_archive.open(filename, 'r')
                files.append((filename, fp.read()))
                fp.close()

        try:
            files = get_files_from_zipfile(os.path.join(save_dir, 'upload.zip'))
            save_cnxml(save_dir, cnxml, files)
            validate_cnxml(cnxml)
        except ConversionError as e:
            return render_conversionerror(request, e.msg)

        # Return to preview
        return HTTPFound(location=request.route_url('preview'), request=request)

    # Read CNXML
    with open(cnxml_filename, 'rt') as fp:
        cnxml = fp.read()

    # Clean CNXML
    cnxml = clean_cnxml(cnxml)
    cnxml = cnxml.decode('utf-8')
    cnxml = unicode(cnxml)

    return {
        'codemirror': True,
        'form': FormRenderer(form),
        'cnxml': cnxml,
        'transformerror': transformerror,
    }


class SummaryView(BaseHelper):

    @view_config(route_name='summary')
    def generate_html_view(self):
        self.check_login()
        templatePath = 'templates/summary.pt'
        
        request = self.request
        deposit_receipt = request.session['deposit_receipt']
        response = parse_sword_treatment.get_requirements(deposit_receipt)
        response['view'] = self
        return render_to_response(
            templatePath, response, request=request)


class ConfigSchema(formencode.Schema):
    allow_extra_fields = True
    service_document_url = formencode.validators.URL(add_http=True)
    workspace_url = formencode.validators.URL(add_http=True)
    title = formencode.validators.String()
    summary = formencode.validators.String()
    subject = formencode.validators.Set()
    keywords = formencode.validators.String()
    language = formencode.validators.String(not_empty=True)
    google_code = formencode.validators.String()
    authors = formencode.validators.String()
    maintainers = formencode.validators.String()
    copyright = formencode.validators.String()
    editors = formencode.validators.String()
    translators = formencode.validators.String()


@view_config(route_name='admin_config', renderer='templates/admin_config.pt')
def admin_config_view(request):
    """
    Configure default UI parameter settings
    """

    check_login(request)
    session = request.session
    subjects = ["Arts", "Business", "Humanities", "Mathematics and Statistics",
                "Science and Technology", "Social Sciences"]
    form = Form(request, schema=ConfigSchema)
    config = load_config(request)

    # Check for successful form completion
    if 'form.submitted' in request.POST:
        form.validate()
        for key in ['service_document_url', 'workspace_url']:
            config[key] = form.data[key]
        for key in ['title', 'summary', 'subject', 'keywords', 'language', 'google_code']:
            config['metadata'][key] = form.data[key]
        for key in ['authors', 'maintainers', 'copyright', 'editors', 'translators']:
            config['metadata'][key] = [x.strip() for x in form.data[key].split(',')]
        save_config(config, request)

    response =  {
        'form': FormRenderer(form),
        'subjects': subjects,
        'languages': languages,
        'roles': [('authors', 'Authors'),
                  ('maintainers', 'Maintainers'),
                  ('copyright', 'Copyright holders'),
                  ('editors', 'Editors'),
                  ('translators',
                  'Translators')
                 ],
        'request': request,
        'config': config,
    }
    return response


def get_module_list(connection, workspace):
    xml = sword2cnx.get_module_list(connection, workspace)
    tree = lxml.etree.XML(xml)
    ns_dict = {'xmlns:sword': 'http://purl.org/net/sword/terms/',
               'xmlns': 'http://www.w3.org/2005/Atom'}
    elements =  tree.xpath('/xmlns:feed/xmlns:entry', namespaces=ns_dict)

    modules = []
    for element in elements:
        title_element = element.xpath('./xmlns:title', namespaces=ns_dict)[0]
        title = title_element.text

        link_elements = element.xpath('./xmlns:link[@rel="edit"]',
                                      namespaces=ns_dict
                                     )
        edit_link = link_elements[0].get('href')

        path_elements = edit_link.split('/')
        view_link = '/'.join(path_elements[:-1])
        path_elements.reverse()
        uid = path_elements[1]

        modules.append([uid, edit_link, title, view_link])
    return modules


class MetadataSchema(formencode.Schema):
    allow_extra_fields = True
    title = formencode.validators.String(not_empty=True)
    keep_title = formencode.validators.Bool()
    summary = formencode.validators.String()
    keep_summary = formencode.validators.Bool()
    keywords = formencode.validators.String()
    keep_keywords = formencode.validators.Bool()
    subject = formencode.validators.Set()
    keep_subject = formencode.validators.Bool()
    language = formencode.validators.String(not_empty=True)
    keep_language = formencode.validators.Bool()
    google_code = formencode.validators.String()
    keep_google_code = formencode.validators.Bool()
    workspace = formencode.validators.String(not_empty=True)
    keep_workspace = formencode.validators.Bool()
    authors = formencode.validators.String(not_empty=True)
    maintainers = formencode.validators.String(not_empty=True)
    copyright = formencode.validators.String(not_empty=True)
    editors = formencode.validators.String()
    translators = formencode.validators.String()


class Metadata_View(BaseHelper):
    
    def __init__(self, request):
        super(Metadata_View, self).__init__(request)
        self.check_login()
        self.templatePath = 'templates/metadata.pt'
        self.config = load_config(request)
        self.metadata = self.config['metadata']
        self.featured_links = []
        self.workspaces = \
            [(i['href'], i['title']) for i in self.session['collections']]

        self.role_mappings = {'authors': 'dcterms:creator',
                              'maintainers': 'oerdc:maintainer',
                              'copyright': 'dcterms:rightsHolder',
                              'editors': 'oerdc:editor',
                              'translators': 'oerdc:translator'}

        self.subjects = ["Arts",
                         "Business",
                         "Humanities",
                         "Mathematics and Statistics",
                         "Science and Technology",
                         "Social Sciences",
                         ]

        # The roles fields are comma-separated strings. This makes the javascript
        # easier on the client side, and is easy to parse. The fields are hidden,
        # and the values will be user ids, which should not have commas in them.
        self.field_list = [
            ['authors', 'authors', {'type': 'hidden'}],
            ['maintainers', 'maintainers', {'type': 'hidden'}],
            ['copyright', 'copyright', {'type': 'hidden'}],
            ['editors', 'editors', {'type': 'hidden'}],
            ['translators', 'translators', {'type': 'hidden'}],
            ['title', 'Title', {'type': 'text'}],
            ['summary', 'Summary', {'type': 'textarea'}],
            ['keywords', 'Keywords (One per line)', {'type': 'textarea'}],
            ['subject', 'Subject', {'type': 'checkbox',
                                    'values': self.subjects}],
            ['language', 'Language', {'type': 'select',
                                      'values': languages,
                                      'selected_value': 'en'}],
            ['google_code', 'Google Analytics Code', {'type': 'text'}],
            ['workspace', 'Workspace', {'type': 'select',
                                      'values': self.workspaces}],
        ]

        self.remember_fields = [field[0] for field in self.field_list[5:]]

        # Get remembered fields from the session
        self.defaults = {}

        # Get remembered title from the session    
        if 'title' in self.session:
            self.defaults['title'] = self.session['title']
            self.config['metadata']['title'] = self.session['title']

    def update_session(self, session, remember_fields, form):        
        # Persist the values that should be persisted in the session, and
        # delete the others.
        for field_name in remember_fields:
            if form.data['keep_%s' % field_name]:
                session[field_name] = form.data[field_name]
            else:
                if field_name in session:
                    del(session[field_name])
        return session
    
    def get_metadata_entry(self, form, session):
        metadata = {}
        metadata['dcterms:title'] = form.data['title'] if form.data['title'] \
                                    else session['filename']

        # Summary
        metadata['dcterms:abstract'] = form.data['summary'].strip()

        # Language
        metadata['dcterms:language'] = form.data['language']

        # Subjects
        metadata['oerdc:oer-subject'] = form.data['subject']

        # Keywords
        metadata['dcterms:subject'] = [i.strip() for i in
                                       form.data['keywords'].splitlines()
                                       if i.strip()]

        # Google Analytics code
        metadata['oerdc:analyticsCode'] = form.data['google_code'].strip()

        # Standard change description
        metadata['oerdc:descriptionOfChanges'] = 'Uploaded from external document importer.'

        # Build metadata entry object
        for key in metadata.keys():
            if metadata[key] == '':
                del metadata[key]
        metadata_entry = sword2cnx.MetaData(metadata)

        # Add role tags
        role_metadata = {}
        for k, v in self.role_mappings.items():
            role_metadata[v] = form.data[k].split(',')
        for key, value in role_metadata.iteritems():
            for v in value:
                v = v.strip()
                if v:
                    metadata_entry.add_field(key, '', {'oerdc:id': v})

        return metadata_entry 

    def get_raw_featured_links(self, request):
        data = peppercorn.parse(request.POST.items())
        if data is None or len(data.get('featuredlinks')) < 1:
            return []

        # get featured links from data
        tmp_links = {}
        # first we organise the links by category
        for details in data['featuredlinks']:
            category = details['fl_category']
            tmp_list = tmp_links.get(category, [])
            tmp_list.append(details)
            tmp_links[category] = tmp_list
        return tmp_list

    def add_featured_links(self, request, zip_file, save_dir):
        structure = peppercorn.parse(request.POST.items())
        if structure.has_key('featuredlinks'):
            featuredlinks = build_featured_links(structure)
            if featuredlinks:
                cnxml = get_cnxml_from_zipfile(zip_file)
                new_cnxml = add_featuredlinks_to_cnxml(cnxml,
                                                       featuredlinks)
                files = get_files_from_zipfile(zip_file)
                save_cnxml(save_dir, new_cnxml, files)
        return featuredlinks

    def create_module_with_atompub_xml(self, conn, collection_iri, entry):
        dr = conn.create(col_iri = collection_iri,
                         metadata_entry = entry,
                         in_progress = True)
        return dr

    def update_module(self, save_dir, connection, metadata, module_url):
        zip_file = open(os.path.join(save_dir, 'upload.zip'), 'rb')
        deposit_receipt = connection.update(
            metadata_entry = metadata,
            payload = zip_file,
            filename = 'upload.zip',
            mimetype = 'application/zip',
            packaging = ZIP_PACKAGING,
            edit_iri = module_url,
            edit_media_iri = module_url + '/editmedia',
            metadata_relevant=False,
            in_progress=True)
        zip_file.close()
        return deposit_receipt

    def create_module(self, form, connection, metadata, zip_file): 
        deposit_receipt = connection.create(
            col_iri = form.data['workspace'],
            metadata_entry = metadata,
            payload = zip_file,
            filename = 'upload.zip',
            mimetype = 'application/zip',
            packaging = ZIP_PACKAGING,
            in_progress = True)
        return deposit_receipt

    @reify
    def workspace_popup(self):
        return self.macro_renderer.implementation().macros['workspace_popup']

    @reify
    def featured_link(self):
        return self.macro_renderer.implementation().macros['featured_link']

    @reify
    def featured_links_table(self):
        return self.macro_renderer.implementation().macros['featured_links_table']

    def show_featured_links_form(self):
        return self.metadata.get('featured_link_groups', '') and 'checked' or ''

    def get_title(self, metadata, session):
        return metadata.get('dcterms:title', session.get('title', ''))

    def get_subjects(self, metadata):
        return metadata.get('subjects', [])

    def get_summary(self, metadata):
        return metadata.get('dcterms:abstract', '')
    
    def get_values(self, field):
        return getattr(self, field)

    @reify
    def get_featured_link_groups(self):
        return self.metadata.get('featured_link_groups', [])

    @reify
    def authors(self):
        return self.get_contributors('dcterms:creator', self.metadata)

    @reify
    def maintainers(self):
        return self.get_contributors('oerdc:maintainer', self.metadata)

    @reify
    def copyright(self):
        return self.get_contributors('dcterms:rightsHolder', self.metadata)

    @reify
    def editors(self):
        return self.get_contributors('oerdc:editor', self.metadata)

    @reify
    def translators(self):
        return self.get_contributors('oerdc:translator', self.metadata)
    
    def get_contributors(self, role, metadata):
        delimeter = ','
        default = self.get_default(role)
        val = metadata.get(role, default)
        if isinstance(val, types.ListType):
            val = delimeter.join(val)
        return val

    def get_default(self, role):
        for k, v in self.role_mappings.items():
            if v == role:
                break
        return self.defaults.get(k, [])

    def get_language(self, metadata):
        default = self.defaults.get('language')
        return metadata.get('dcterms:language', default)

    def get_keywords(self, metadata):
        delimeter = '\n'
        val = metadata.get('keywords', '')
        if isinstance(val, types.ListType):
            val = delimeter.join(val) 
        return val

    def get_google_code(self, metadata):
        return metadata.get('oerdc:analyticsCode', '')

    def get_strength_image_name(self, link):
        return 'strength%s.png' % link.strength

    @view_config(route_name='metadata')
    def generate_html_view(self):
        """
        Handle metadata adding and uploads
        """
        session = self.session
        request = self.request
        config = self.config
        workspaces = self.workspaces
        subjects = self.subjects
        field_list = self.field_list
        remember_fields = self.remember_fields
        defaults = self.defaults

        form = Form(request,
                    schema=MetadataSchema,
                    defaults=defaults
                   )

        # Check for successful form completion
        if form.validate():
            self.update_session(session, remember_fields, form)

            # Reconstruct the path to the saved files
            save_dir = os.path.join(
                request.registry.settings['transform_dir'],
                session['upload_dir']
            )

            # Create a connection to the sword service
            conn = self.get_connection()

            # Send zip file to Connexions through SWORD interface
            with open(os.path.join(save_dir, 'upload.zip'), 'rb') as zip_file:
                # Create the metadata entry
                metadata_entry = self.get_metadata_entry(form, session)
                self.featured_links = self.add_featured_links(request,
                                                              zip_file,
                                                              save_dir)

                associated_module_url = request.POST.get('associated_module_url')
                if associated_module_url:
                    # this is an update not a create
                    deposit_receipt = self.update_module(
                        save_dir, conn, metadata_entry, associated_module_url)
                else:
                    # this is a workaround until I can determine why the 
                    # featured links don't upload correcly with a multipart
                    # upload during module creation. See redmine issue 40
                    # TODO:
                    # Fix me properly!
                    if self.featured_links:
                        deposit_receipt = create_module_in_2_steps(
                            form, conn, metadata_entry, zip_file, save_dir)
                    else:
                        deposit_receipt = self.create_module(
                            form, conn, metadata_entry, zip_file)

            # Remember to which workspace we submitted
            session['deposit_workspace'] = workspaces[[x[0] for x in workspaces].index(form.data['workspace'])][1]

            # The deposit receipt cannot be pickled, so we pickle the xml
            session['deposit_receipt'] = deposit_receipt.to_xml()

            # Go to the upload page
            return HTTPFound(location=request.route_url('summary'))

        module_url = request.POST.get('module', None)
        metadata = config['metadata']
        username = self.session['username']
        password = self.session['password']
        if module_url:
            metadata.update(get_metadata_from_repo(session, module_url, username, password))
        else:
            for role in ['authors', 'maintainers', 'copyright', 'editors', 'translators']:
                self.defaults[role] = ','.join(
                    self.config['metadata'][role]).replace('_USER_', username)

                self.config['metadata'][role] = ', '.join(
                    self.config['metadata'][role]).replace('_USER_', username)
                
                self.defaults['language'] = \
                    self.config['metadata'].get('language', u'en')

        selected_workspace = request.POST.get('workspace', None)
        selected_workspace = selected_workspace or workspaces[0][0]
        workspace_title = [w[1] for w in workspaces if w[0] == selected_workspace][0]
        response =  {
            'form': FormRenderer(form),
            'field_list': field_list,
            'workspaces': workspaces,
            'selected_workspace': selected_workspace,
            'workspace_title': workspace_title,
            'module_url': module_url,
            'languages': languages,
            'subjects': subjects,
            'config': config,
            'macros': self.macro_renderer,
            'metadata': metadata,
            'session': session,
            'view': self,
        }
        return render_to_response(self.templatePath, response, request=request)

class ModuleAssociationSchema(formencode.Schema):
    allow_extra_fields = True
    module = formencode.validators.String()


class Module_Association_View(BaseHelper):

    # NOTE: Your implementation class *must* define these actions if you want
    # to reuse the navigation and batch macros.
    navigation_actions = {'next': 'metadata', 
                          'previous': 'preview',
                          'batch': 'module_association'}

    @view_config(route_name='module_association',
                 renderer='templates/module_association.pt')
    def generate_html_view(self):
        request = self.request

        self.check_login()
        config = load_config(request)
        conn = self.get_connection()

        workspaces = [
            (i['href'], i['title']) for i in self.session['collections']
        ]
        selected_workspace = request.params.get('workspace', workspaces[0][0])
        workspace_title = [w[1] for w in workspaces if w[0] == selected_workspace][0]

        b_start = int(request.GET.get('b_start', '0'))
        b_size = int(request.GET.get('b_size', config.get('default_batch_size')))

        modules = get_module_list(conn, selected_workspace)
        modules = Batch(modules, start=b_start, size=b_size)
        module_macros = get_renderer('templates/modules_list.pt').implementation()

        form = Form(request, schema=ModuleAssociationSchema)
        response = {'form': FormRenderer(form),
                    'workspaces': workspaces,
                    'selected_workspace': selected_workspace,
                    'workspace_title': workspace_title,
                    'modules': modules,
                    'request': request,
                    'config': config,
                    'module_macros': module_macros,
                    'view': self,
        }
        return response

    @reify
    def macros(self):
        return self.macro_renderer.implementation().macros

    @reify
    def workspace_list(self):
        return self.macro_renderer.implementation().macros['workspace_list']

    @reify
    def workspace_popup(self):
        return self.macro_renderer.implementation().macros['workspace_popup']

    @reify
    def modules_list(self):
        return self.macro_renderer.implementation().macros['modules_list']
    
class Modules_List_View(BaseHelper):
    # NOTE: Your implementation class *must* define these actions if you want
    # to reuse the navigation and batch macros.
    navigation_actions = {'next': 'choose', 
                          'previous': 'metadata',
                          'batch': 'module_association'}

    """ Show a list of all the modules in a workspace.
    """
    @view_config(
        route_name='modules_list', renderer="templates/modules_list.pt")
    def generate_html_view(self):
        self.check_login()
        config = load_config(self.request)
        conn = self.get_connection()

        selected_workspace = self.session['collections'][0]['href']
        selected_workspace = self.request.params.get('workspace',
                                                     selected_workspace)
        print "Workspace url: " + selected_workspace

        modules = get_module_list(conn, selected_workspace)
        b_start = int(self.request.GET.get('b_start', '0'))
        b_size = int(self.request.GET.get('b_size', 
                                          config.get('default_batch_size')))
        modules = Batch(modules, start=b_start, size=b_size)

        response = {'selected_workspace': selected_workspace,
                    'modules': modules,
                    'request': self.request,
                    'config': config,
                    'view': self,
        }
        return response

    @reify
    def modules_list(self):
        return self.macro_renderer.implementation().macros['modules_list']


class Choose_Module(Module_Association_View):

    # NOTE: Your implementation class *must* define these actions if you want
    # to reuse the navigation and batch macros.
    navigation_actions = {'next': 'preview', 
                          'previous': 'choose',
                          'batch': 'choose-module'}

    @view_config(
        route_name='choose-module', renderer="templates/choose_module.pt")
    def generate_html_view(self):
        return super(Choose_Module, self).generate_html_view()

    @reify
    def content_macro(self):
        return self.macro_renderer.implementation().macros['content_macro']


class UploadSchema(formencode.Schema):
    allow_extra_fields = True
    upload = formencode.validators.FieldStorageUploadConverter()


class Choose_Document_Source(BaseHelper):

    navigation_actions = {'next': '', 
                          'previous': '/',
                          'batch': ''}

    @view_config(route_name='choose')
    def generate_html_view(self):
        self.check_login()

        templatePath = 'templates/choose.pt'

        form = Form(self.request, schema=UploadSchema)
        field_list = [('upload', 'File')]

        # clear the session
        if 'transformerror' in self.request.session:
            del self.request.session['transformerror']
        if 'title' in self.request.session:
            del self.request.session['title']

        # Check for successful form completion
        if form.validate():
            try: # Catch-all exception block
                message = 'The file was successfully converted.'

                # Create a directory to do the conversions
                temp_dir_name, save_dir = self.create_work_dir(self.request)

                # Keep the info we need for next uploads.  Note that this
                # might kill the ability to do multiple tabs in parallel,
                # unless it gets offloaded onto the form again.
                self.request.session['upload_dir'] = temp_dir_name
                if form.data.get('newmodule'):
                    # save empty cnxml and html files
                    cnxml = self.empty_cnxml()
                    files = []
                    save_cnxml(save_dir, cnxml, files)
                
                elif form.data.get('existingmodule'):
                    return HTTPFound(
                        location=self.request.route_url('choose-module'))

                elif form.data['upload'] is not None:
                    self.request.session['filename'] = form.data['upload'].filename
                    self.process_document_data(form, self.request, save_dir)

                # Google Docs Conversion
                # if we have a Google Docs ID and Access token.
                elif form.data.get('gdocs_resource_id'):
                    self.process_gdoc_data(form, self.request, save_dir)

                # HTML URL Import:
                elif form.data.get('url_text'):
                    errors = self.process_url_data(self.request, save_dir)
                    if errors:
                        self.request['errors'] = errors
                        response = {'form': FormRenderer(form),
                                    'view': self, }
                        return render_to_response(
                            templatePath, response, request=self.request)

                # Office, CNXML-ZIP or LaTeX-ZIP file
                else:
                    self.process_document_data(form, self.request, save_dir)

            except ConversionError as e:
                return render_conversionerror(self.request, e.msg)

            except Exception:
                tb = traceback.format_exc()
                self.write_traceback_to_zipfile(
                    tb, self.request, temp_dir_name, form)

                templatePath = 'templates/error.pt'
                response = {'traceback': tb}
                if('title' in self.request.session):
                    del self.request.session['title']
                return render_to_response(templatePath, response, request=self.request)

            self.request.session.flash(message)
            return HTTPFound(location=self.request.route_url('preview'))

        # First view or errors
        response = {
            'form': FormRenderer(form),
            'field_list': field_list,
            'view': self,
        }
        return render_to_response(templatePath, response, request=self.request)

    def process_gdoc_data(self, form, request, save_dir):
        gdocs_resource_id = form.data['gdocs_resource_id']
        gdocs_access_token = form.data['gdocs_access_token']

        form.data['gdocs_resource_id'] = None
        form.data['gdocs_access_token'] = None

        title, filename = self.process_gdocs_resource(
            save_dir, gdocs_resource_id, gdocs_access_token)

        self.request.session['title'] = title
        self.request.session['filename'] = filename
    
    def process_gdocs_resource(self, save_dir, gdocs_resource_id, gdocs_access_token=None):

        # login to gdocs and get a client object
        gd_client = getAuthorizedGoogleDocsClient()

        # Create a AuthSub Token based on gdocs_access_token String
        auth_sub_token = gdata.gauth.AuthSubToken(gdocs_access_token) \
                         if gdocs_access_token \
                         else None

        # get the Google Docs Entry
        gd_entry = gd_client.GetDoc(gdocs_resource_id, None, auth_sub_token)

        # Get the contents of the document
        gd_entry_url = gd_entry.content.src
        html = gd_client.get_file_content(gd_entry_url, auth_sub_token)

        # Transformation and get images
        cnxml, objects = gdocs_to_cnxml(html, bDownloadImages=True)

        cnxml = clean_cnxml(cnxml)
        save_cnxml(save_dir, cnxml, objects.items())

        validate_cnxml(cnxml)

        # Return the title and filename.  Old comment states
        # that returning this filename might kill the ability to
        # do multiple tabs in parallel, unless it gets offloaded
        # onto the form again.
        return (gd_entry.title.text, "Google Document")

    def create_work_dir(self, request):
        now_string = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        # TODO: This has a good chance of being unique, but even so...
        temp_dir_name = '%s-%s' % (request.session['username'], now_string)
        save_dir = os.path.join(
            request.registry.settings['transform_dir'],
            temp_dir_name
            )
        os.mkdir(save_dir)
        return temp_dir_name, save_dir

    def process_url_data(self, form, request, save_dir):
        url = form.data['url_text']

        form.data['url_text'] = None

        # Build a regex for Google Docs URLs
        regex = re.compile("^https:\/\/docs\.google\.com\/.*document\/[^\/]\/([^\/]+)\/")
        r = regex.search(url)

        # Take special action for Google Docs URLs
        if r:
            gdocs_resource_id = r.groups()[0]
            title, filename = self.process_gdocs_resource(
                    save_dir, "document:" + gdocs_resource_id)

            request.session['title'] = title
            request.session['filename'] = filename
        else:
            # download html:
            # Simple urlopen() will fail on mediawiki websites like e.g. Wikipedia!
            import_opener = urllib2.build_opener()
            import_opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            try:
                import_request = import_opener.open(url)
                html = import_request.read()

                # transformation
                cnxml, objects, html_title = htmlsoup_to_cnxml(
                        html, bDownloadImages=True, base_or_source_url=url)
                request.session['title'] = html_title

                cnxml = clean_cnxml(cnxml)
                save_cnxml(save_dir, cnxml, objects.items())

                # Keep the info we need for next uploads.  Note that
                # this might kill the ability to do multiple tabs in
                # parallel, unless it gets offloaded onto the form
                # again.
                request.session['filename'] = "HTML Document"

                validate_cnxml(cnxml)

            except urllib2.URLError, e:
                return ['The URL %s could not be opened' %url,]

    def process_document_data(self, form, request, save_dir):
        # Save the original file so that we can convert, plus keep it.
        original_filename = str(os.path.join(
            save_dir,
            form.data['upload'].filename.replace(os.sep, '_'))
        )

        saved_file = open(original_filename, 'wb')
        input_file = form.data['upload'].file
        shutil.copyfileobj(input_file, saved_file)
        saved_file.close()
        input_file.close()

        form.data['upload'] = None

        # Check if it is a ZIP file with at least index.cnxml or a LaTeX file in it
        try:
            zip_archive = zipfile.ZipFile(original_filename, 'r')
            is_zip_archive = ('index.cnxml' in zip_archive.namelist())

            # Do we have a latex file?
            if not is_zip_archive:
                # incoming latex.zip must contain a latex.tex file, where "latex" is the base name.
                (latex_head, latex_tail) = os.path.split(original_filename)
                (latex_root, latex_ext)  = os.path.splitext(latex_tail)
                latex_basename = latex_root
                latex_filename = latex_basename + '.tex'
                is_latex_archive = (latex_filename in zip_archive.namelist())

        except zipfile.BadZipfile:
            is_zip_archive = False
            is_latex_archive = False

        # ZIP package from previous conversion
        if is_zip_archive:
            # Unzip into transform directory
            zip_archive.extractall(path=save_dir)

            # Rename ZIP file so that the user can download it again
            os.rename(original_filename, os.path.join(save_dir, 'upload.zip'))

            # Read CNXML
            with open(os.path.join(save_dir, 'index.cnxml'), 'rt') as fp:
                cnxml = fp.read()

            # Convert the CNXML to XHTML for preview
            html = cnxml_to_htmlpreview(cnxml)
            with open(os.path.join(save_dir, 'index.xhtml'), 'w') as index:
                index.write(html)

            cnxml = clean_cnxml(cnxml)
            validate_cnxml(cnxml)

        # LaTeX
        elif is_latex_archive:
            f = open(original_filename)
            latex_archive = f.read()

            # LaTeX 2 CNXML transformation
            cnxml, objects = latex_to_cnxml(latex_archive, original_filename)

            cnxml = clean_cnxml(cnxml)
            save_cnxml(save_dir, cnxml, objects.items())
            validate_cnxml(cnxml)

        # OOo / MS Word Conversion
        else:
            # Convert from other office format to odt if needed
            filename, extension = os.path.splitext(original_filename)
            odt_filename = str(filename) + '.odt'

            if(extension != '.odt'):
                converter = JOD.DocumentConverterClient()
                # Checks to see if JOD is active on the machine. If it is the
                # conversion occurs using JOD else it converts using OO headless
                if jod_check.check('office[0-9]'):
                    try:
                        converter.convert(original_filename, 'odt', filename + '.odt')
                    except Exception as e:
                        print e
                else:
                    odt_filename= '%s.odt' % filename
                    command = '/usr/bin/soffice -headless -nologo -nofirststartwizard "macro:///Standard.Module1.SaveAsOOO(' + escape_system(original_filename)[1:-1] + ',' + odt_filename + ')"'
                    os.system(command)
                try:
                    fp = open(odt_filename, 'r')
                    fp.close()
                except IOError as io:
                    raise ConversionError("%s not found" %
                                          original_filename)
            
            # Convert and save all the resulting files.

            tree, files, errors = transform(odt_filename)
            cnxml = clean_cnxml(etree.tostring(tree))

            save_cnxml(save_dir, cnxml, files.items())

            # now validate with jing
            validate_cnxml(cnxml)

    def format_info(self, traceback, commit_hash, request, form):
        def format_form_data(key, form):
            return key + ': ' + str(form.data.get(key))

        form_data = "\n".join([format_form_data(key, form) for key in \
            ['gdocs_resource_id', 'gdocs_access_token', 'url_text']]) + "\n"
        
        # Get timestamp
        timestamp = datetime.datetime.now()

        info = \
            """TRACEBACK
            """ + traceback + """

            GIT VERSION
            """ + commit_hash + """

            USER
            """ + request.session['username'] + """

            SERVICE DOCUMENT URL
            """ + request.session['service_document_url'] + """

            TIMESTAMP
            """ + str(timestamp) + """

            FORM DATA
            """ + form_data
        return info

    def get_commit_hash(self):
        try:
            p = subprocess.Popen(["git","log","-1"], stdout=subprocess.PIPE)
            out, err = p.communicate()
            commit_hash = out[:out.find('\n')]
        except OSError:
            commit_hash = 'None'

        return commit_hash

    def write_traceback_to_zipfile(self, traceback, request, temp_dir_name, form):
        # Record traceback

        # Get software version from git
        commit_hash = self.get_commit_hash()
        
        # get the path to the error zip file
        zip_filename = os.path.join(
            request.registry.settings['errors_dir'],
            temp_dir_name + '.zip'
        )

        # Zip up error report, form data, uploaded file (if any)  and
        # temporary transform directory
        zip_archive = zipfile.ZipFile(zip_filename, 'w')
        info = self.format_info(traceback, commit_hash, request, form)
        zip_archive.writestr("info.txt", info)

        basePath = request.registry.settings['transform_dir']
        add_directory_to_zip(temp_dir_name,
                             zip_archive,
                             basePath=basePath)

    def empty_cnxml(self):
        config = load_config(self.request)
        filepath = config['blank_cnxml_file'] 
        with open(filepath, 'rb') as cnxmlfile:
            content = cnxmlfile.read()
        return content

