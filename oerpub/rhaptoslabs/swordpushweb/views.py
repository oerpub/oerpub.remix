import os
import shutil
import datetime
import zipfile
from lxml import etree
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render_to_response
from pyramid.response import Response

import formencode

from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer

from languages import languages
from sword2.deposit_receipt import Deposit_Receipt
from oerpub.rhaptoslabs import sword2cnx
from rhaptos.cnxmlutils.odt2cnxml import transform
from oerpub.rhaptoslabs.cnxml2htmlpreview.cnxml2htmlpreview import cnxml_to_htmlpreview
import gdata.gauth
import gdata.docs.client
from oerpub.rhaptoslabs.html_gdocs2cnxml.gdocs_authentication import getAuthorizedGoogleDocsClient
from oerpub.rhaptoslabs.html_gdocs2cnxml.gdocs2cnxml import gdocs_to_cnxml
import urllib2
from oerpub.rhaptoslabs.html_gdocs2cnxml.htmlsoup2cnxml import htmlsoup_to_cnxml

from utils import escape_system, clean_cnxml, pretty_print_dict, load_config, save_config, add_directory_to_zip

TESTING = False


def check_login(request, raise_exception=True):
    # Check if logged in
    for key in ['username', 'password', 'service_document_url']:
        if not request.session.has_key(key):
            if raise_exception:
                raise HTTPFound(location=request.route_url('login'))
            else:
                return False
    return True


class LoginSchema(formencode.Schema):
    allow_extra_fields = True
    service_document_url = formencode.validators.String(not_empty=True)
    username = formencode.validators.PlainText(not_empty=True)
    password = formencode.validators.PlainText(not_empty=True)


@view_config(route_name='login')
def login_view(request):
    """
    Perform a 'login' by getting the service document from a sword repository.
    """

    templatePath = 'templates/%s/login.pt'%(['novice','expert'][request.session.get('expert_mode', False)])

    config = load_config(request)

    form = Form(request, schema=LoginSchema)
    field_list = [
        ('username',),
        ('password',),
    ]
    
    session = request.session

    # Check for successful form completion
    if 'form.submitted' in request.POST and form.validate():
        # The login details are persisted on the session
        for field_name in [i[0] for i in field_list]:
            session[field_name] = form.data[field_name]
        session['service_document_url'] = form.data['service_document_url']
        loggedIn = True
    # Check if user is already authenticated
    else:
        loggedIn = True
        for key in ['username', 'password', 'service_document_url']:
            if not session.has_key(key):
                loggedIn = False

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
            response = {
                'form': FormRenderer(form),
                'field_list': field_list,
                'config': config,
                'login_error': "Invalid username or password. Please try again.",
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


@view_config(route_name='logout', renderer='templates/login.pt')
def logout_view(request):
    session = request.session
    session.invalidate()
    raise HTTPFound(location=request.route_url('login'))


@view_config(route_name='switch_expert_mode')
def switch_expert_mode_view(request):
    referer = request.environ.get('HTTP_REFERER', request.route_url('login'))
    # HACK: to make frames view of preview page work out
    substr = '/preview_side'
    if referer[-len(substr):] == substr:
        referer = referer[:-len(substr)] + '/preview'
    # /HACK
    request.session['expert_mode'] = not request.session.get('expert_mode', False)
    raise HTTPFound(location=referer)


class UploadSchema(formencode.Schema):
    allow_extra_fields = True
    upload = formencode.validators.FieldStorageUploadConverter()


@view_config(route_name='choose')
def choose_view(request):
    check_login(request)

    templatePath = 'templates/%s/choose.pt'%(['novice','expert'][request.session.get('expert_mode', False)])

    form = Form(request, schema=UploadSchema)
    field_list = [('upload', 'File')]

    # Check for successful form completion
    if 'form.submitted' in request.POST and form.validate():
        try: # Catch-all exception block
            # Create a directory to do the conversions
            now_string = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            # TODO: This has a good chance of being unique, but even so...
            temp_dir_name = '%s-%s' % (request.session['username'], now_string)
            save_dir = os.path.join(
                request.registry.settings['transform_dir'],
                temp_dir_name
                )
            os.mkdir(save_dir)

            # Google Docs Conversion
            # if we have a Google Docs ID and Access token.
            if form.data['gdocs_resource_id']:
                gdocs_resource_id = form.data['gdocs_resource_id']
                gdocs_access_token = form.data['gdocs_access_token']

                # TODO: Do the Google Docs transformation here

                # login to gdocs and get a client object
                gd_client = getAuthorizedGoogleDocsClient()

                # Create a AuthSub Token based on gdocs_access_token String
                auth_sub_token = gdata.gauth.AuthSubToken(gdocs_access_token)

                # get the Google Docs Entry
                gd_entry = gd_client.GetDoc(gdocs_resource_id, None, auth_sub_token)

                # Get the contents of the document
                gd_entry_url = gd_entry.content.src
                html = gd_client.get_file_content(gd_entry_url, auth_sub_token)

                # Transformation and get images
                cnxml, objects = gdocs_to_cnxml(html, bDownloadImages=True)

                # write CNXML output
                cnxml_filename = os.path.join(save_dir, 'index.cnxml')
                cnxml_file = open(cnxml_filename, 'w')
                try:
                    cnxml_file.write(cnxml)
                    cnxml_file.flush()
                finally:
                    cnxml_file.close()

                # write images
                for image_filename, image in objects.iteritems():
                    image_filename = os.path.join(save_dir, image_filename)
                    image_file = open(image_filename, 'wb') # write binary, important!
                    try:
                        image_file.write(image)
                        image_file.flush()
                    finally:
                        image_file.close()

                htmlpreview = cnxml_to_htmlpreview(cnxml)
                with open(os.path.join(save_dir, 'index.xhtml'), 'w') as index:
                    index.write(htmlpreview)

                # Zip up all the files. This is done now, since we have all the files
                # available, and it also allows us to post a simple download link.
                # Note that we cannot use zipfile as context manager, as that is only
                # available from python 2.7
                # TODO: Do a filesize check xxxx
                zip_archive = zipfile.ZipFile(os.path.join(save_dir, 'upload.zip'), 'w')
                try:
                    zip_archive.writestr('index.cnxml', cnxml)
                    for image_filename, image in objects.iteritems():
                        zip_archive.writestr(image_filename, image)
                finally:
                    zip_archive.close()

                # Keep the info we need for next uploads.  Note that this might kill
                # the ability to do multiple tabs in parallel, unless it gets offloaded
                # onto the form again.
                request.session['upload_dir'] = temp_dir_name
                request.session['filename'] = "Google Document"

            # HTML URL Import:
            elif form.data.get('url_text'):
                url = form.data['url_text']

                # download html:
                html = urllib2.urlopen(url).read()

                # transformation            
                cnxml = htmlsoup_to_cnxml(html)

                # write CNXML output
                cnxml_filename = os.path.join(save_dir, 'index.cnxml')
                cnxml_file = open(cnxml_filename, 'w')
                try:
                    cnxml_file.write(cnxml)
                    cnxml_file.flush()
                finally:
                    cnxml_file.close()

                # write images, not stable yet -> look at Gdocs code. TODO!

                htmlpreview = cnxml_to_htmlpreview(cnxml)
                with open(os.path.join(save_dir, 'index.xhtml'), 'w') as index:
                    index.write(htmlpreview)

                # Zip up all the files. This is done now, since we have all the files
                # available, and it also allows us to post a simple download link.
                # Note that we cannot use zipfile as context manager, as that is only
                # available from python 2.7
                # TODO: Do a filesize check xxxx
                zip_archive = zipfile.ZipFile(os.path.join(save_dir, 'upload.zip'), 'w')
                try:
                    zip_archive.writestr('index.cnxml', cnxml)
                    #for image_filename, image in objects.iteritems():
                    #    zip_archive.writestr(image_filename, image)
                finally:
                    zip_archive.close()

                # Keep the info we need for next uploads.  Note that this might kill
                # the ability to do multiple tabs in parallel, unless it gets offloaded
                # onto the form again.
                request.session['upload_dir'] = temp_dir_name
                request.session['filename'] = "HTML Document"

            # Office or ZIP file
            else:
                # Save the original file so that we can convert, plus keep it.
                original_filename = os.path.join(
                    save_dir,
                    form.data['upload'].filename.replace(os.sep, '_'))
                saved_file = open(original_filename, 'wb')
                input_file = form.data['upload'].file
                shutil.copyfileobj(input_file, saved_file)
                saved_file.close()
                input_file.close()

                # Check if it is a ZIP file with at least index.cnxml in it
                try:
                    zip_archive = zipfile.ZipFile(original_filename, 'r')
                    is_zip_archive = ('index.cnxml' in zip_archive.namelist())
                except zipfile.BadZipfile:
                    is_zip_archive = False

                # ZIP package from previous conversion
                if is_zip_archive:
                    # Unzip into transform directory
                    zip_archive.extractall(path=save_dir)

                    # Rename ZIP file so that the user can download it again
                    os.rename(original_filename, os.path.join(save_dir, 'upload.zip'))

                    # Read CNXML
                    with open(os.path.join(save_dir, 'index.cnxml'), 'rt') as fp:
                        xml = fp.read()

                    # Convert the CNXML to XHTML for preview
                    html = cnxml_to_htmlpreview(xml)
                    with open(os.path.join(save_dir, 'index.xhtml'), 'w') as index:
                        index.write(html)

                # OOo / MS Word Conversion
                else:
                    # Convert from other office format to odt if needed
                    odt_filename = original_filename
                    filename, extension = os.path.splitext(original_filename)
                    if extension != '.odt':
                        odt_filename = '%s.odt' % filename
                        command = '/usr/bin/soffice -headless -nologo -nofirststartwizard "macro:///Standard.Module1.SaveAsOOO(' + escape_system(original_filename)[1:-1] + ',' + odt_filename + ')"'
                        os.system(command)

                    # Convert and save all the resulting files.
                    tree, files, errors = transform(odt_filename)
                    xml = etree.tostring(tree)
                    with open(os.path.join(save_dir, 'index.cnxml'), 'w') as cnxml_file:
                        cnxml_file.write(xml)
                    for filename, content in files.items():
                        with open(os.path.join(save_dir, filename), 'wb') as img_file:
                            img_file.write(content)

                    # Convert the cnxml for preview.
                    html = cnxml_to_htmlpreview(xml)
                    with open(os.path.join(save_dir, 'index.xhtml'), 'w') as index:
                        index.write(html)

                    # Zip up all the files. This is done now, since we have all the files
                    # available, and it also allows us to post a simple download link.
                    # Note that we cannot use zipfile as context manager, as that is only
                    # available from python 2.7
                    # TODO: Do a filesize check xxxx
                    zip_archive = zipfile.ZipFile(os.path.join(save_dir, 'upload.zip'), 'w')
                    try:
                        zip_archive.writestr('index.cnxml', xml.encode('utf8'))
                        for filename, content in files.items():
                            zip_archive.writestr(filename, content)
                    finally:
                        zip_archive.close()

                # Keep the info we need for next uploads.  Note that this might kill
                # the ability to do multiple tabs in parallel, unless it gets offloaded
                # onto the form again.
                request.session['upload_dir'] = temp_dir_name
                request.session['filename'] = form.data['upload'].filename
        except Exception:
            # Record traceback
            import traceback
            tb = traceback.format_exc()
            # Get software version from git
            try:
                import subprocess
                p = subprocess.Popen(["git","log","-1"], stdout=subprocess.PIPE)
                out, err = p.communicate()
                commit_hash = out[:out.find('\n')]
            except OSError:
                commit_hash = 'None'
            # Get timestamp
            timestamp = datetime.datetime.now()
            # Zip up error report, form data, uploaded file (if any)  and temporary transform directory
            zip_filename = os.path.join(request.registry.settings['errors_dir'], temp_dir_name + '.zip')
            zip_archive = zipfile.ZipFile(zip_filename, 'w')
            zip_archive.writestr("info.txt", """TRACEBACK
""" + tb + """
GIT VERSION
""" + commit_hash + """

USER
""" + request.session['username'] + """

SERVICE DOCUMENT URL
""" + request.session['service_document_url'] + """

TIMESTAMP
""" + str(timestamp) + """

FORM DATA
""" + '\n'.join([key + ': ' + str(form.data.get(key)) for key in ['gdocs_resource_id', 'gdocs_access_token', 'url_text']]) + "\n")
            add_directory_to_zip(temp_dir_name, zip_archive, basePath=request.registry.settings['transform_dir'])

            templatePath = 'templates/error.pt'
            response = {
                'traceback': tb,
            }
            return render_to_response(templatePath, response, request=request)

        request.session.flash('The file was successfully converted.')
        return HTTPFound(location=request.route_url('preview_frames'))

    # First view or errors
    response = {
        'form': FormRenderer(form),
        'field_list': field_list,
    }
    return render_to_response(templatePath, response, request=request)


@view_config(route_name='preview_frames', renderer='templates/preview_frames.pt')
def preview_frames_view(request):
    check_login(request)

    body_filename = request.session.get('preview-no-cache')
    if body_filename is None:
        body_filename = 'index.xhtml'
    else:
        del request.session['preview-no-cache']

    return {
        'header_url': request.route_url('preview_header'),
        #'body_url': '%s%s/index.xhtml'%(request.static_url('oerpub.rhaptoslabs.swordpushweb:transforms/'), request.session['upload_dir']),
        'body_url': request.route_url('preview_body'),
    }


@view_config(route_name='preview_header')
def preview_header_view(request):
    check_login(request)
    templatePath = 'templates/%s/preview_header.pt'%(['novice','expert'][request.session.get('expert_mode', False)])
    return render_to_response(templatePath, {}, request=request)


@view_config(route_name='preview_side', renderer='templates/preview_side.pt')
def preview_side_view(request):
    return {'expert_mode_switch_target': '_parent'}


@view_config(route_name='preview_body')
def preview_body_view(request):
    return HTTPFound('%s%s/index.xhtml'%(request.static_url('oerpub.rhaptoslabs.swordpushweb:transforms/'), request.session['upload_dir']),
                     headers={'Cache-Control': 'max-age=0, must-revalidate', 'Expires': 'Sun, 3 Dec 2000 00:00:00 GMT'},
                     request=request)


class CnxmlSchema(formencode.Schema):
    allow_extra_fields = True
    cnxml = formencode.validators.String(not_empty=True)


@view_config(route_name='cnxml', renderer='templates/expert/cnxml_editor.pt')
def cnxml_view(request):
    check_login(request)

    form = Form(request, schema=CnxmlSchema)

    save_dir = os.path.join(request.registry.settings['transform_dir'], request.session['upload_dir'])
    cnxml_filename = os.path.join(save_dir, 'index.cnxml')

    # Check for successful form completion
    if 'cnxml' in request.POST and form.validate():
        import time
        html_filename = os.path.join(save_dir, 'index.xhtml')
        zip_filename = os.path.join(save_dir, 'upload.zip')

        # Make backup of CNXML and HTML preview
        os.rename(cnxml_filename, cnxml_filename + '~')
        os.rename(html_filename, html_filename + '~')
        os.rename(zip_filename, zip_filename + '~')

        # Save new CNXML
        with open(cnxml_filename, 'wt') as fp:
            fp.write(form.data['cnxml'])

        # Convert the CNXML for preview
        html = cnxml_to_htmlpreview(form.data['cnxml'])
        with open(html_filename, 'w') as index:
            index.write(html)

        # Update ZIP package
        old_zip_archive = zipfile.ZipFile(zip_filename + '~', 'r')
        zip_archive = zipfile.ZipFile(zip_filename, 'w')
        try:
            zip_archive.writestr('index.cnxml', form.data['cnxml'].encode('utf8'))
            for filename in old_zip_archive.namelist():
                if filename == 'index.cnxml':
                    continue
                fp = old_zip_archive.open(filename, 'r')
                zip_archive.writestr(filename, fp.read())
                fp.close()
        finally:
            zip_archive.close()

        # Return to preview
        return HTTPFound(location=request.route_url('preview_frames'), request=request)

    # Read CNXML
    with open(cnxml_filename, 'rt') as fp:
        cnxml = fp.read()

    # Clean CNXML
    cnxml = clean_cnxml(cnxml)

    return {
        'codemirror': True,
        'form': FormRenderer(form),
        'cnxml': cnxml,
    }


@view_config(route_name='summary')
def summary_view(request):
    check_login(request)
    templatePath = 'templates/%s/summary.pt'%(['novice','expert'][request.session.get('expert_mode', False)])

    # Note: need to extract the version string before passing dom to
    # Deposit_Receipt, which mangles dom.
    dom = etree.fromstring(request.session['deposit_receipt'])
    version_string = dom.find('{http://www.w3.org/2005/Atom}generator').text.strip()
    dr = Deposit_Receipt(dom=dom)
    treatment = dr.treatment

    import parse_sword_treatment
    response = parse_sword_treatment.markdown(treatment)
    if (version_string == 'uri:"rhaptos.swordservice.plone" version:"1.0"') and (treatment.find('Publication requirements:') != -1):
        response.update(parse_sword_treatment.cnx_1_0(treatment))
    elif (version_string == 'uri:"rhaptos.swordservice.plone" version:"1.0"') and (treatment.find('Before publishing:') != -1):
        response.update(parse_sword_treatment.test_server_1_0(treatment))
    else:
        print 'WARNING: No valid version number found in SWORD deposit receipt. Defaulting to showing the SWORD treatment as is.'

    return render_to_response(templatePath, response, request=request)


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


@view_config(route_name='metadata')
def metadata_view(request):
    """
    Handle metadata adding and uploads
    """
    check_login(request)
    templatePath = 'templates/%s/metadata.pt'%(['novice','expert'][request.session.get('expert_mode', False)])
    session = request.session
    config = load_config(request)

    workspaces = [(i['href'], i['title']) for i in session['collections']]
    subjects = ["Arts",
                "Business",
                "Humanities",
                "Mathematics and Statistics",
                "Science and Technology",
                "Social Sciences",
                ]
    # The roles fields are comma-separated strings. This makes the javascript
    # easier on the client side, and is easy to parse. The fields are hidden,
    # and the values will be user ids, which should not have commas in them.
    field_list = [
                  ['authors', 'authors', {'type': 'hidden'}],
                  ['maintainers', 'maintainers', {'type': 'hidden'}],
                  ['copyright', 'copyright', {'type': 'hidden'}],
                  ['editors', 'editors', {'type': 'hidden'}],
                  ['translators', 'translators', {'type': 'hidden'}],
                  ['title', 'Title', {'type': 'text'}],
                  ['summary', 'Summary', {'type': 'textarea'}],
                  ['keywords', 'Keywords (One per line)', {'type': 'textarea'}],
                  ['subject', 'Subject', {'type': 'checkbox',
                                          'values': subjects}],
                  ['language', 'Language', {'type': 'select',
                                            'values': languages,
                                            'selected_value': 'en'}],
                  ['google_code', 'Google Analytics Code', {'type': 'text'}],
                  ['workspace', 'Workspace', {'type': 'select',
                                            'values': workspaces}],
                  ]
    remember_fields = [field[0] for field in field_list[5:]]

    # Get remembered fields from the session
    defaults = {}
    for role in ['authors', 'maintainers', 'copyright', 'editors', 'translators']:
        defaults[role] = ','.join(config['metadata'][role]).replace('_USER_', session['username'])
        config['metadata'][role] = ', '.join(config['metadata'][role]).replace('_USER_', session['username'])

    """
    for field_name in remember_fields:
        if field_name in session:
            defaults[field_name] = session[field_name]
            defaults['keep_%s' % field_name] = True
    """

    form = Form(request,
                schema=MetadataSchema,
                defaults=defaults
                )

    # Check for successful form completion
    if form.validate():

        # Persist the values that should be persisted in the session, and
        # delete the others.
        for field_name in remember_fields:
            if form.data['keep_%s' % field_name]:
                session[field_name] = form.data[field_name]
            else:
                if field_name in session:
                    del(session[field_name])

        # Reconstruct the path to the saved files
        save_dir = os.path.join(
            request.registry.settings['transform_dir'],
            session['upload_dir']
            )

        # Create the metadata entry
        metadata = {}

        # Title
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
        role_mappings = {'authors': 'dcterms:creator',
                         'maintainers': 'oerdc:maintainer',
                         'copyright': 'dcterms:rightsHolder',
                         'editors': 'oerdc:editor',
                         'translators': 'oerdc:translator'}
        for k, v in role_mappings.items():
            role_metadata[v] = form.data[k].split(',')
        for key, value in role_metadata.iteritems():
            for v in value:
                v = v.strip()
                if v:
                    metadata_entry.add_field(key, '', {'oerdc:id': v})

        if not TESTING:
            # Create a connection to the sword service
            conn = sword2cnx.Connection(session['service_document_url'],
                                       user_name=session['username'],
                                       user_pass=session['password'],
                                       always_authenticate=True,
                                       download_service_document=False)

            # Send zip file to Connexions through SWORD interface
            with open(os.path.join(save_dir, 'upload.zip'), 'rb') as zip_file:
                deposit_receipt = conn.create(
                    col_iri = form.data['workspace'],
                    metadata_entry = metadata_entry,
                    payload = zip_file,
                    filename = 'upload.zip',
                    mimetype = 'application/zip',
                    packaging = 'http://purl.org/net/sword/package/SimpleZip',
                    in_progress = True)

        # Remember to which workspace we submitted
        session['deposit_workspace'] = workspaces[[x[0] for x in workspaces].index(form.data['workspace'])][1]

        if not TESTING:
            # The deposit receipt cannot be pickled, so we pickle the xml
            session['deposit_receipt'] = deposit_receipt.to_xml()
        else:
            session['deposit_receipt'] = """<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:sword="http://purl.org/net/sword/"
       xmlns:dcterms="http://purl.org/dc/terms/"
       xmlns:md="http://cnx.rice.edu/mdml"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xmlns:oerdc="http://cnx.org/aboutus/technology/schemas/oerdc">

    <!-- SWORD deposit receipt -->
    <title>Word created with multipart</title>
    <id>module.2011-10-06.9527952926</id>
    <updated>2011/10/06 15:29:15.879 Universal</updated>
    <summary type="text">A bit of summary.</summary>
    <generator uri="rhaptos.swordservice.plone" version="1.0"> uri:"rhaptos.swordservice.plone" version:"1.0"</generator>

    <!-- The metadata begins -->
    <dcterms:identifier xsi:type="dcterms:URI">http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926</dcterms:identifier> 
    <dcterms:identifier xsi:type="oerdc:Version">**new**</dcterms:identifier> 
    <dcterms:identifier xsi:type="oerdc:ContentId">module.2011-10-06.9527952926</dcterms:identifier> 
    <dcterms:title>Word created with multipart</dcterms:title>
    <dcterms:created>2011/10/06 15:29:12.821 Universal</dcterms:created> 
    <dcterms:modified>2011/10/06 15:29:15.879 Universal</dcterms:modified> 
    <dcterms:creator oerdc:id="user1"
                     oerdc:email="useremail1@localhost.net"
                     oerdc:pending="False">firstname1 lastname1</dcterms:creator>
    <dcterms:creator oerdc:id="roche"
                     oerdc:email="roche@upfrontsystems.co.za"
                     oerdc:pending="True">Roche Compaan</dcterms:creator>
    <dcterms:creator oerdc:id="user2"
                     oerdc:email="useremail2@localhost.net"
                     oerdc:pending="True">firstname2 lastname2</dcterms:creator>
    <oerdc:maintainer oerdc:id="user1"
                      oerdc:email="useremail1@localhost.net"
                      oerdc:pending="False">firstname1 lastname1</oerdc:maintainer>
    <oerdc:maintainer oerdc:id="roche"
                      oerdc:email="roche@upfrontsystems.co.za"
                      oerdc:pending="True">Roche Compaan</oerdc:maintainer>
    <dcterms:rightsHolder oerdc:id="roche"
                          oerdc:email="roche@upfrontsystems.co.za"
                          oerdc:pending="True">Roche Compaan</dcterms:rightsHolder>
    <dcterms:rightsHolder oerdc:id="user2"
                          oerdc:email="useremail2@localhost.net"
                          oerdc:pending="True">firstname2 lastname2</dcterms:rightsHolder>
    <oerdc:translator oerdc:id="user85"
                      oerdc:email="dcwill@rice.edu"
                      oerdc:pending="True">Daniel Williamson</oerdc:translator>
    <oerdc:editor oerdc:id="user3"
                  oerdc:email="useremail3@localhost.net"
                  oerdc:pending="True">firstname3 lastname3</oerdc:editor>
    <!-- CNX-Supported but not in MDML -->
    <oerdc:descriptionOfChanges>
        This is brand new.
    </oerdc:descriptionOfChanges> 
    <oerdc:oer-subject>Arts</oerdc:oer-subject>
    <dcterms:subject xsi:type="oerdc:Subject">Arts</dcterms:subject>
    <dcterms:subject>music</dcterms:subject>
    <dcterms:subject>passion</dcterms:subject>
    <dcterms:abstract>A bit of summary.</dcterms:abstract>
    <dcterms:language xsi:type="ISO639-1">es</dcterms:language> 
    <dcterms:license xsi:type="dcterms:URI"></dcterms:license>
    <sword:treatment>
        Module 'Word created with multipart' was imported via the SWORD API.
        You can <a href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/module_view">preview your module here</a> to see what it will look like once it is published.
        
        The current description of the changes you have made for this version of the module: This is brand new.
        

        
        Publication requirements:
        
            1. Author (firstname1 lastname1, account:user1), will need to <a href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/module_publish">sign the license here.</a>
        
        
            2. Author (Roche Compaan, account:roche), will need to <a href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/module_publish">sign the license here.</a>
        
        
            3. Author (firstname2 lastname2, account:user2), will need to <a href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/module_publish">sign the license here.</a>
        
        
            4. You cannot publish with pending role requests. Contributor, Roche Compaan (account:roche),
must <a href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/collaborations?user=roche">agree to thw pending requests</a>.
        
        
            5. You cannot publish with pending role requests. Contributor, Daniel Williamson (account:user85),
must <a href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/collaborations?user=user85">agree to thw pending requests</a>.
        
        
            6. You cannot publish with pending role requests. Contributor, firstname2 lastname2 (account:user2),
must <a href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/collaborations?user=user2">agree to thw pending requests</a>.
        
        
            7. You cannot publish with pending role requests. Contributor, firstname3 lastname3 (account:user3),
must <a href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/collaborations?user=user3">agree to thw pending requests</a>.
        
        
    </sword:treatment>
    <!-- For all UNPUBLISHED modules -->
    <link rel="alternate"
          href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/module_view?format=html"/>
    <content type="application/zip"
             src="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/sword/editmedia"/>
    <link rel="edit-media"
          href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/sword/editmedia"/>
    <link rel="edit"
          href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/sword"/>
    <link rel="http://purl.org/net/sword/terms/add"
          href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/sword"/>
    <link rel="http://purl.org/net/sword/terms/statement"
          type="application/atom+xml;type=feed"
          href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/sword/statement.atom"/>
    <sword:packaging>http://purl.org/net/sword/package/SimpleZip</sword:packaging>
    <link rel="http://purl.org/net/sword/terms/derivedResource"
          href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/module_view?format=html"/>
    <link rel="http://purl.org/net/sword/terms/derivedResource"
          href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/"/>
    <link rel="http://purl.org/net/sword/terms/derivedResource"
          type="application/pdf"
          href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/module_view?format=pdf"/>
    <link rel="http://purl.org/net/sword/terms/derivedResource"
          type="application/zip"
          href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/module_export?format=zip"/>
    <link rel="http://purl.org/net/sword/terms/derivedResource"
          type="application/xml"
          href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/module_export?format=plain"/>
    <!-- END for all UNPUBLISHED modules -->
</entry>
"""

        # Go to the upload page
        return HTTPFound(location=request.route_url('summary'))

    response =  {
        'form': FormRenderer(form),
        'field_list': field_list,
        'workspaces': workspaces,
        'languages': languages,
        'subjects': subjects,
        'config': config,
    }
    return render_to_response(templatePath, response, request=request)


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
        'roles': [('authors', 'Authors'), ('maintainers', 'Maintainers'), ('copyright', 'Copyright holders'), ('editors', 'Editors'), ('translators', 'Translators')],
        'request': request,
        'config': config,
    }
    return response
