import os
import shutil
import datetime
import zipfile
import markdown
from lxml import etree
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

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

# TODO: If we have enough helper functions, they should go into utils

def escape_system(input_string):
    return '"' + input_string.replace('\\', '\\\\').replace('"', '\\"') + '"'

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
    field_list = [
                  ('username', 'User Name'),
                  ('password', 'Password', {'type': 'password'}),
                  ]

    # Check for successful form completion
    if 'form.submitted' in request.POST and form.validate():

        # The login details are persisted on the session
        session = request.session
        for field_name in [i[0] for i in field_list]:
            session[field_name] = form.data[field_name]
        session['service_document_url'] = form.data['service_document_url']

        # Get the service document and persist what's needed.
        conn = sword2cnx.Connection(form.data['service_document_url'],
                                   user_name=form.data['username'],
                                   user_pass=form.data['password'],
                                   always_authenticate=True,
                                   download_service_document=True)


        try:
            # Get available collections from SWORD service document
            # We create a list of dictionaries, otherwise we'll have problems
            # pickling them.
            session['collections'] = [{'title': i.title, 'href': i.href} for i
                                      in sword2cnx.get_workspaces(conn)]
        except:
            session.flash('Could not log in', 'errors')
            return {'form': FormRenderer(form), 'field_list': field_list}

        if len(session['collections']) > 1:
            session.flash('You have more than one workspace. Please check that you have selected the correct one before uploading anything.')


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
        return HTTPFound(location="/choose")
    return {
        'form': FormRenderer(form),
        'field_list': field_list,
        }

@view_config(route_name='logout', renderer='templates/login.pt')
def logout_view(request):
    session = request.session
    session.invalidate()
    raise HTTPFound(location='/')

class UploadSchema(formencode.Schema):
    allow_extra_fields = True
    upload = formencode.validators.FieldStorageUploadConverter()

@view_config(route_name='choose', renderer='templates/choose.pt')
def upload_view(request):
    form = Form(request, schema=UploadSchema)
    field_list = [('upload', 'File')]

    # Check for successful form completion
    if 'form.submitted' in request.POST and form.validate():
          
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
            
            # transformation and get images
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
            with open(os.path.join(save_dir, 'index.html'), 'w') as index:
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
            request.session['filename'] = gd_entry_url

        # OOo / MS Word Conversion
        else:
            # Save the original file so that we can convert, plus keep it.
            original_filename = os.path.join(
                save_dir,
                form.data['upload'].filename.replace(os.sep, '_'))
            saved_odt = open(original_filename, 'wb')
            input_file = form.data['upload'].file
            shutil.copyfileobj(input_file, saved_odt)
            saved_odt.close()
            input_file.close()

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
            with open(os.path.join(save_dir, 'index.html'), 'w') as index:
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

        # TODO: Errors should be shown to the user
        request.session.flash('The file was successfully converted.')

        return HTTPFound(location="/preview")

    # First view or errors
    return {
        'form': FormRenderer(form),
        'field_list': field_list,
        }

@view_config(route_name='preview', renderer='templates/preview.pt')
def preview_view(request):
    session = request.session
    session.flash('Previewing file: %s' % session['filename'])
    return {}

@view_config(route_name='sword_treatment',
             renderer='templates/sword_treatment.pt')
def sword_treatment_view(request):
    session = request.session
    dr = Deposit_Receipt(xml_deposit_receipt=session['deposit_receipt'])

    # TODO: Here be dragons. The following bit of code is designed to
    # specifically convert the Connexions treatment reply to something that we
    # can push through a markdown filter to get reasonable-looking html. By
    # default, the first couple of paragraphs are indented, which gets you
    # <pre> tags, which strips out links. Ugh.

    treatment = [i.lstrip() for i in dr.treatment.split('\n')]
    treatment = markdown.markdown('\n'.join(treatment))
    return {'treatment': treatment}

@view_config(route_name='summary', renderer='templates/summary.pt')
def summary_view(request):
    return {}

@view_config(route_name='roles', renderer='templates/roles.pt')
def roles_view(request):
    return {}

class MetadataSchema(formencode.Schema):
    allow_extra_fields = True
    title = formencode.validators.String(not_empty=True)
    keep_title = formencode.validators.Bool()
    summary = formencode.validators.String(not_empty=True)
    keep_summary = formencode.validators.Bool()
    keywords = formencode.validators.String(not_empty=True)
    keep_keywords = formencode.validators.Bool()
    subject = formencode.validators.Set()
    keep_subject = formencode.validators.Bool()
    language = formencode.validators.String(not_empty=True)
    keep_language = formencode.validators.Bool()
    google_code = formencode.validators.String()
    keep_google_code = formencode.validators.Bool()
    workspace = formencode.validators.String(not_empty=True)
    keep_workspace = formencode.validators.Bool()

@view_config(route_name='metadata', renderer='templates/metadata.pt')
def metadata_view(request):
    """
    Handle metadata adding and uploads
    """
    session = request.session
    session.flash('Uploading: %s' % session['filename'])

    workspaces = [(i['href'], i['title']) for i in session['collections']]
    subjects = ["Arts",
                "Business",
                "Humanities",
                "Mathematics and Statistics",
                "Science and Technology",
                "Social Sciences",
                ]
    field_list = [['title', 'Title'],
                  ['summary', 'Summary', {'type': 'textarea'}],
                  ['keywords', 'Keywords (One per line)', {'type': 'textarea'}],
                  ['subject', 'Subject', {'type': 'checkbox',
                                          'values': subjects}],
                  ['language', 'Language', {'type': 'select',
                                            'values': languages,
                                            'selected_value': 'en'}],
                  ['google_code', 'Google Analytics Code'],
                  ['workspace', 'Workspace', {'type': 'select',
                                            'values': workspaces}],
                  ]
    remember_fields = [field[0] for field in field_list]

    # Get remembered fields from the session
    defaults = {}
    for field_name in remember_fields:
        if field_name in session:
            defaults[field_name] = session[field_name]
            defaults['keep_%s' % field_name] = True

    form = Form(request,
                schema=MetadataSchema,
                defaults=defaults
                )

    # Check for successful form completion
    if 'form.submitted' in request.POST and form.validate():

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
        role_metadata = {'dcterms:creator': [session['username']],
                        'dcterms:rightsHolder': [session['username']],
                        'oerdc:maintainer': [session['username'], 'siyavula'],
                        }
        for key, value in role_metadata.iteritems():
            for v in value:
                v = v.strip()
                if v:
                    metadata_entry.add_field(key, '', {'oerdc:id': v})

        # Create a connection to the sword service
        conn = sword2cnx.Connection(session['service_document_url'],
                                   user_name=session['username'],
                                   user_pass=session['password'],
                                   always_authenticate=True,
                                   download_service_document=True)

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

        # The deposit receipt cannot be pickled, so we pickle the xml
        session['deposit_receipt'] = deposit_receipt.to_xml()
        # Go to the upload page
        return HTTPFound(location="/summary")
    return {
        'form': FormRenderer(form),
        'field_list': field_list,
        }
