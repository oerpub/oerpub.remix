import os
import re
import time
import shutil
import zipfile
import urllib2
import datetime
import traceback
import formencode
import shlex, subprocess
from logging import getLogger

from lxml import etree
import httplib2
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import AccessTokenCredentials

from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid_simpleform.renderers import FormRenderer

from rhaptos.cnxmlutils.odt2cnxml import transform

from oerpub.rhaptoslabs.html_gdocs2cnxml.htmlsoup2cnxml import htmlsoup_to_cnxml
from oerpub.rhaptoslabs.html_gdocs2cnxml.gdocs_authentication import getAuthorizedGoogleDocsClient
from oerpub.rhaptoslabs.cnxml2htmlpreview.cnxml2htmlpreview import cnxml_to_htmlpreview
from oerpub.rhaptoslabs.latex2cnxml.latex2cnxml import latex_to_cnxml
from oerpub.rhaptoslabs.html_gdocs2cnxml.gdocs2cnxml import gdocs_to_cnxml

import gdata.gauth
import gdata.docs.client
from helpers import BaseHelper
# Imports JOD convert script
from oerpub.rhaptoslabs.swordpushweb import convert as JOD
#Imports script which checks to see if JOD is running
from oerpub.rhaptoslabs.swordpushweb import jod_check
from oerpub.rhaptoslabs.swordpushweb.interfaces import IWorkflowSteps
from oerpub.rhaptoslabs.swordpushweb.views.utils import (
    load_config,
    save_zip,
    clean_cnxml,
    save_cnxml,
    validate_cnxml,
    check_login,
    escape_system,
    add_directory_to_zip,
    render_conversionerror,
    ZIP_PACKAGING,
    LATEX_PACKAGING,
    UNKNOWN_PACKAGING,
    remove_save_dir,
    create_save_dir,)
from oerpub.rhaptoslabs.swordpushweb.errors import (
    ConversionError,
    UnknownPackagingError)

LOG = getLogger('%s' % __name__)


class NewOrExistingSchema(formencode.Schema):
    allow_extra_fields = True
    newmodule = formencode.validators.Bool()
    existingmodule = formencode.validators.Bool()
    neworexistingmodule = formencode.validators.NotEmpty()

class OfficeDocumentUploadSchema(formencode.Schema):
    allow_extra_fields = True
    upload_file = formencode.validators.FieldStorageUploadConverter()

class GoogleDocsSchema(formencode.Schema):
    allow_extra_fields = True
    gdocs_resource_id = formencode.validators.NotEmpty()
    #gdocs_access_token = formencode.validators.NotEmpty()

class URLSchema(formencode.Schema):
    allow_extra_fields = True
    url_text = formencode.validators.URL()

class PresentationSchema(formencode.Schema):
    allow_extra_fields = True
    importer = formencode.validators.FieldStorageUploadConverter()
    #upload_to_ss = formencode.validators.String()
    #upload_to_google = formencode.validators.String()
    #introductory_paragraphs = formencode.validators.String()

class ZipOrLatexSchema(formencode.Schema):
    allow_extra_fields = True
    upload_zip_file = formencode.validators.FieldStorageUploadConverter()


class Choose_Document_Source(BaseHelper):

    @view_config(route_name='choose')
    def process(self):
        super(Choose_Document_Source, self)._process()
        self.do_transition()
        return self.navigate()

    def do_transition(self):
        request = self.request
        session = request.session
        self.clear_session(request, session)
    
    def clear_session(self, request, session):
        ''' Remove all known application specific state from the session.
        '''
        keys = ['transformerror',
                'title',
                'source',
                'target',
                'module_url',
                'upload_dir',
                'source_module_url',
                'target_module_url',
                'preview-no-cache',]
        for key in keys:
            if key in session:
                del session[key]

        # cleanup the temporary work areas too
        remove_save_dir(request)

        
    def navigate(self, errors=None, form=None):
        request = self.request
        neworexisting_form = Form(request, schema=NewOrExistingSchema)
        officedocument_form = Form(request, schema=OfficeDocumentUploadSchema)
        googledocs_form = Form(request, schema=GoogleDocsSchema)
        url_form = Form(request, schema=URLSchema)
        presentationform = Form(request, schema=PresentationSchema)
        zip_or_latex_form = Form(request, schema=ZipOrLatexSchema)

        LOG.info(presentationform.all_errors())

        #TODO: This can be replaced by utility/adapter lookups
        # Check for successful form completion
        if neworexisting_form.validate():
            return self._process_neworexisting_submit(request, neworexisting_form)
        elif officedocument_form.validate():
            return self._process_officedocument_submit(request, officedocument_form)
        elif googledocs_form.validate():
            return self._process_googledocs_submit(request, googledocs_form)
        elif url_form.validate():
            return self._process_url_submit(request, url_form)
        elif presentationform.validate():
            return self._process_presentationform_submit(request, presentationform)
        elif zip_or_latex_form.validate():
            return self._process_zip_or_latex_form(request, zip_or_latex_form)

        templatePath = 'templates/choose.pt'
        # First view or errors
        response = {
            'neworexisting_form': FormRenderer(neworexisting_form),
            'officedocument_form': FormRenderer(officedocument_form),
            'googledocs_form': FormRenderer(googledocs_form),
            'url_form': FormRenderer(url_form),
            'presentationform': FormRenderer(presentationform),
            'zip_or_latex_form': FormRenderer(zip_or_latex_form),
            'view': self,
        }
        return render_to_response(templatePath, response, request=self.request)

    def _process_neworexisting_submit(self, request, form):
        LOG.info('process new or existing submit')
        processor = NewOrExistingModuleProcessor(request)
        return processor.process(form)

    def _process_officedocument_submit(self, request, form):
        LOG.info('process wordprocessor submit')
        processor = OfficeDocumentProcessor(request, form)
        return processor.process(form)
    
    def _process_googledocs_submit(self, request, form):
        LOG.info('process google doc submit')
        processor = GoogleDocProcessor(request)
        return processor.process(form)
    
    def _process_presentationform_submit(self, request, form):
        LOG.info('process presentation submit')
        processor = PresentationProcessor(request, form)
        return processor.process(form)
    
    def _process_zip_or_latex_form(self, request, form):
        LOG.info('process zip or latex submit')
        processor = ZipOrLatexModuleProcessor(request, form)
        return processor.process(form)

    def _process_url_submit(self, request, form):
        LOG.info('process URL submit')
        processor = URLProcessor(request)
        return processor.process(form)

class BaseFormProcessor(object):
    def __init__(self, request):
        self.request = request
        self.message = 'The file was successfully converted.'
        request.session['source'] = 'undefined'

        # Leave these empty at first
        self._temp_dir_name = None
        self._save_dir = None
        self._upload_dir = None

    def _tmp(self):
        """ This is called by the temp_dir_name, upload_dir and save_dir
            properties below. The idea is that you allocate temporary space
            the second one of these properties is touched and no sooner. """
        if self._upload_dir is None:
            self._temp_dir_name, self._save_dir = self.create_save_dir(
                self.request)
            self._upload_dir = self._temp_dir_name
            self.request.session['upload_dir'] = self._upload_dir
        return (self._upload_dir, self._save_dir)

    @property
    def temp_dir_name(self):
        return self.upload_dir

    @property
    def upload_dir(self):
        return self._tmp()[0]

    @property
    def save_dir(self):
        return self._tmp()[1]
        

    @classmethod
    def save_original_file(self, filename, input_file):
        # Save the original file so that we can convert, plus keep it.
        saved_file = open(filename, 'wb')
        shutil.copyfileobj(input_file, saved_file)
        saved_file.close()

    def create_save_dir(self, request):
        return create_save_dir(request)

    def write_traceback_to_zipfile(self, traceback, form=None):
        # Record traceback

        if self._temp_dir_name is None:
            # No files to zip just yet, just return
            return

        # Get software version from git
        commit_hash = self.get_commit_hash()
        
        # get the path to the error zip file
        zip_filename = os.path.join(
            self.request.registry.settings['errors_dir'],
            self._temp_dir_name + '.zip'
        )

        # Zip up error report, form data, uploaded file (if any)  and
        # temporary transform directory
        zip_archive = zipfile.ZipFile(zip_filename, 'w')
        if form is not None:
            info = self.format_info(traceback, commit_hash, self.request, form)
            zip_archive.writestr("info.txt", info)

        basePath = self.request.registry.settings['transform_dir']
        add_directory_to_zip(self._temp_dir_name,
                             zip_archive,
                             basePath=basePath)

    def get_commit_hash(self):
        try:
            p = subprocess.Popen(["git","log","-1"], stdout=subprocess.PIPE)
            out, err = p.communicate()
            commit_hash = out[:out.find('\n')]
        except OSError:
            commit_hash = 'None'

        return commit_hash

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

    def set_source(self, source):
        self.request.session['source'] = source

    def get_source(self):
        return self.request.session.get('source', 'undefined')

    def set_target(self, target):
        self.request.session['target'] = target

    def get_target(self):
        return self.request.session.get('target', 'undefined')
    
    def nextStep(self):
        workflowsteps = self.request.registry.getUtility(IWorkflowSteps)
        source = self.get_source()
        target = self.get_target()
        current_step = 'choose'
        return workflowsteps.getNextStep(source, target, current_step)

class NewOrExistingModuleProcessor(BaseFormProcessor):
    def __init__(self, request):
        super(NewOrExistingModuleProcessor, self).__init__(request)
        self.set_source('new')
        self.set_target('new')

    def process(self, form):
        try:
            if form.data.get('newmodule'):
                self.set_source('new')
                self.set_target('new')
                # save empty cnxml and html files
                cnxml = self.empty_cnxml()
                files = []
                save_cnxml(self.save_dir, cnxml, files)
            
            elif form.data.get('existingmodule'):
                self.set_source('existingmodule')
                self.set_target('existingmodule')
                return HTTPFound(
                    location=self.request.route_url('choose-module'))

        except ConversionError as e:
            return render_conversionerror(self.request, e.msg)
        
        # TODO: add a process decorator that has this bit of error handling
        except Exception:
            tb = traceback.format_exc()
            self.write_traceback_to_zipfile(tb, form)
            templatePath = 'templates/error.pt'
            response = {'traceback': tb}
            if('title' in self.request.session):
                del self.request.session['title']
            return render_to_response(templatePath, response, request=self.request)

        self.request.session.flash(self.message)
        return HTTPFound(location=self.request.route_url(self.nextStep()))
        
    def empty_cnxml(self):
        config = load_config(self.request)
        filepath = config['blank_cnxml_file'] 
        with open(filepath, 'rb') as cnxmlfile:
            content = cnxmlfile.read()
        return content

class ZipOrLatexModuleProcessor(BaseFormProcessor):
    def __init__(self, request, form):
        super(ZipOrLatexModuleProcessor, self).__init__(request)
        ufname = form.data['upload_zip_file'].filename.replace(os.sep, '_')
        self.original_filename = os.path.join(self.save_dir, ufname)

        # Save the original file so that we can convert, plus keep it.
        saved_file = open(self.original_filename, 'wb')
        input_file = form.data['upload_zip_file'].file
        shutil.copyfileobj(input_file, saved_file)
        saved_file.close()
        input_file.close()

        self.zip_archive = zipfile.ZipFile(self.original_filename, 'r')
        form.data['upload_zip_file'] = None
        self.set_source('cnxinputs')
        self.set_target('new')

    def process(self, form):
        try:
            processor = None
            packaging = self.get_type()
            if packaging == ZIP_PACKAGING:
                processor = ZipFileProcessor(self.request, form)
                return processor.process(self.original_filename)
            elif packaging == LATEX_PACKAGING:
                processor = LatexProcessor(self.request)
                return processor.process(form)

        except UnknownPackagingError as e:
            return render_conversionerror(self.request, e.msg)

        except Exception:
            tb = traceback.format_exc()
            self.write_traceback_to_zipfile(tb, form)
            templatePath = 'templates/error.pt'
            response = {'traceback': tb}
            if('title' in self.request.session):
                del self.request.session['title']
            return render_to_response(templatePath, response, request=self.request)

        self.request.session.flash(self.message)
        return HTTPFound(location=self.request.route_url(self.nextStep()))
    
    def get_type(self):
        # Check if it is a ZIP file with at least index.cnxml or a LaTeX file in it
        result = UNKNOWN_PACKAGING
        try:
            is_zip_archive = ('index.cnxml' in self.zip_archive.namelist())

            # Do we have a latex file?
            if is_zip_archive:
                result = ZIP_PACKAGING
            else:
                # incoming latex.zip must contain a latex.tex file, where
                # "latex" is the base name.
                (latex_head, latex_tail) = os.path.split(self.original_filename)
                (latex_root, latex_ext)  = os.path.splitext(latex_tail)
                latex_basename = latex_root
                latex_filename = latex_basename + '.tex'
                is_latex_archive = (latex_filename in self.zip_archive.namelist())
                if is_latex_archive:
                    result = LATEX_PACKAGING

        except zipfile.BadZipfile:
            raise UnknownPackagingError(
                'Could not find type for %s' % self.original_filename)

        return result

class ZipFileProcessor(BaseFormProcessor):
    def __init__(self, request, form):
        super(ZipFileProcessor, self).__init__(request)
        self.set_source('cnxinputs')
        self.set_target('new')

    def process(self, zip_filename):
        try:
            self.zip_archive = zipfile.ZipFile(zip_filename, 'r')

            # Unzip into transform directory
            self.zip_archive.extractall(path=self.save_dir)

            # Rename ZIP file so that the user can download it again
            os.rename(zip_filename,
                      os.path.join(self.save_dir, 'upload.zip'))

            # Read CNXML
            with open(os.path.join(self.save_dir, 'index.cnxml'), 'rt') as fp:
                cnxml = fp.read()

            # Convert the CNXML to XHTML for preview
            html = cnxml_to_htmlpreview(cnxml)
            with open(os.path.join(self.save_dir, 'index.xhtml'), 'w') as index:
                index.write(html)

            cnxml = clean_cnxml(cnxml)
            validate_cnxml(cnxml)

        except ConversionError as e:
            return render_conversionerror(self.request, e.msg)

        except Exception:
            tb = traceback.format_exc()
            self.write_traceback_to_zipfile(tb, form)
            templatePath = 'templates/error.pt'
            response = {'traceback': tb}
            if('title' in self.request.session):
                del self.request.session['title']
            return render_to_response(templatePath, response, request=self.request)

        self.request.session.flash(self.message)
        return HTTPFound(location=self.request.route_url(self.nextStep()))

class LatexProcessor(BaseFormProcessor):
    def __init__(self, request):
        super(LatexProcessor, self).__init__(request)
        self.set_source('cnxinputs')
        self.set_target('new')

    def process(self, form):
        try:
            f = open(self.original_filename)
            latex_archive = f.read()

            # LaTeX 2 CNXML transformation
            cnxml, objects = latex_to_cnxml(latex_archive, self.original_filename)

            cnxml = clean_cnxml(cnxml)
            save_cnxml(self.save_dir, cnxml, objects.items())
            validate_cnxml(cnxml)

        except ConversionError as e:
            return render_conversionerror(self.request, e.msg)

        except Exception:
            tb = traceback.format_exc()
            self.write_traceback_to_zipfile(tb, form)
            templatePath = 'templates/error.pt'
            response = {'traceback': tb}
            if('title' in self.request.session):
                del self.request.session['title']
            return render_to_response(templatePath, response, request=self.request)

        self.request.session.flash(self.message)
        return HTTPFound(location=self.request.route_url(self.nextStep()))

class OfficeDocumentProcessor(BaseFormProcessor):
    def __init__(self, request, form):
        super(OfficeDocumentProcessor, self).__init__(request)
        self.set_source('fileupload')
        self.set_target('new')
        ufname = form.data['upload_file'].filename.replace(os.sep, '_')
        self.original_filename = os.path.join(self.save_dir, ufname)
        self.request.session['filename'] = form.data['upload_file'].filename
        self.save_original_file(self.original_filename, form.data['upload_file'].file)

    def process(self, form):
        try:
            # Convert from other office format to odt if needed
            filename, extension = os.path.splitext(self.original_filename)
            odt_filename = str(filename) + '.odt'

            if(extension != '.odt'):
                self._convert_to_odt(filename)        
            # Convert and save all the resulting files.

            tree, files, errors = transform(odt_filename)
            cnxml = clean_cnxml(etree.tostring(tree))

            save_cnxml(self.save_dir, cnxml, files.items())

            # now validate with jing
            validate_cnxml(cnxml)

        except ConversionError as e:
            return render_conversionerror(self.request, e.msg)

        except Exception:
            tb = traceback.format_exc()
            self.write_traceback_to_zipfile(tb, form)
            templatePath = 'templates/error.pt'
            response = {'traceback': tb}
            if('title' in self.request.session):
                del self.request.session['title']
            return render_to_response(templatePath, response, request=self.request)

        self.request.session.flash(self.message)
        return HTTPFound(location=self.request.route_url(self.nextStep()))
    
    def _convert_to_odt(self,filename):
        converter = JOD.DocumentConverterClient()
        # Checks to see if JOD is active on the machine. If it is the
        # conversion occurs using JOD else it converts using OO headless
        command = None
        odt_filename = '%s.odt' % filename
        if jod_check.check('office[0-9]'):
            try:
                converter.convert(self.original_filename, 'odt', odt_filename)
            except Exception as e:
                LOG.error(e)
                raise ConversionError(e)
        else:
            escaped_ofn = escape_system(self.original_filename)[1:-1]
            # XXX Should we not also escape odt_filename?
            macro = 'macro:///Standard.Module1.SaveAsOOO(%s,%s)' % (escaped_ofn, odt_filename)
            command = '%s %s %s %s %s' % ('/usr/bin/soffice',
                                          '--headless',
                                          '--nologo',
                                          '--nofirststartwizard',
                                          macro)
            command = shlex.split(command.encode('utf-8'))
            process = subprocess.Popen(command,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE)
            stdout, stderr = process.communicate()

        try:
            # wait for the file to exist
            count = 0
            while not os.path.isfile(odt_filename) and count < 10:
                count += 1
                LOG.info('Waiting for file, retry count:%s' % count)
                time.sleep(1) 
            fp = open(odt_filename, 'r')
            fp.close()
        except IOError as io:
            if command == None:
                raise ConversionError("%s not found" %
                                      self.original_filename)
            else:
                raise ConversionError(
                    "%s not found because command \"%s\" failed" %
                    (odt_filename,command) )
        
class GoogleDocProcessor(BaseFormProcessor):
    """ This processor is a little insane. In working with the existing scheme
        here, it has a process() method, but all that does is send you over to
        google for authentication. The actual processing is implemented in the
        callback() method. """

    def __init__(self, request):
        super(GoogleDocProcessor, self).__init__(request)
        self.set_source('gdocupload')
        self.set_target('new')

    def process(self, form):
        gdocs_resource_id = form.data['gdocs_resource_id']

        # First attempt to get the document without auth. It is unclear
        # what the official way to do that is, but this works. Fetch the
        # document using the docs export url. If we get a redirect, we assume
        # that is a redirect to a login page and move on to real
        # authentication. Research on the subject suggest that a redirect might
        # also occur if the imported document is too large.
        http = httplib2.Http()
        http.follow_redirects = False
        try:
            # Make sure gdocs_resource_id is safe, we're injecting it
            # into an url and this could potentially be used for all sorts of
            # insertion attacks. This checks that all characters in the
            # resource id is allowed as per RFC 1738.
            assert re.compile("(^[\w$-.+!*'(),]+$)").match(
                gdocs_resource_id) is not None, "Possible insertion attack"
            resp, html = http.request(
                'https://docs.google.com/document/d/%s/export?format=html&confirm=no_antivirus' % gdocs_resource_id)
        except HttpError:
            pass
        else:
            # Check that status was OK, google docs sends a redirect to a login
            # page if not.
            if resp.status / 100 == 2:
                # Get the title
                title = etree.fromstring(html,
                    etree.HTMLParser()).xpath(
                    '/html/head/title/text()')[0] or \
                    'Untitled Google Document'

                return self.process_gdocs_resource(html, title, form)

        # Doc is not public or could not import. Redirect google oath. Because
        # we overrode create_save_dir, we will not leave behind any crud
        # because of this.  This will eventually redirect to callback() below.
        return self.request.registry.velruse_providers['google'].login(
            self.request, docid=gdocs_resource_id)

    def callback(self, request, gdocs_resource_id, gdocs_access_token):
        # This is called when we return from google auth. Fetch the document.
        resp, html, title = self.get_gdoc_resource(gdocs_resource_id,
            gdocs_access_token)
        if resp.status / 100 != 2:
            # TODO, we can handle this a bit better.
            raise HTTPNotFound('Could not download google document')

        # We have the content, now we can create a temporary workspace.
        # In keeping with the scheme above, update the request on which we
        # operate, and update like BaseFormProcessor does above.
        return self.process_gdocs_resource(html, title)

    def process_gdocs_resource(self, html, title, form=None):
        try:
            filename = self._process_gdocs_resource(
                self.save_dir, html)
        except ConversionError as e:
            return render_conversionerror(self.request, e.msg)

        except Exception:
            tb = traceback.format_exc()
            self.write_traceback_to_zipfile(tb, form)
            templatePath = 'templates/error.pt'
            response = {'traceback': tb}
            if('title' in self.request.session):
                del self.request.session['title']
            return render_to_response(templatePath, response, request=self.request)

        self.request.session['title'] = title
        self.request.session['filename'] = filename
        self.request.session.flash(self.message)
        return HTTPFound(location=self.request.route_url(self.nextStep()))

    @classmethod
    def _process_gdocs_resource(klass, save_dir, html):
        # Transformation and get images
        cnxml, objects = gdocs_to_cnxml(html, bDownloadImages=True)
        cnxml = clean_cnxml(cnxml)
        save_cnxml(save_dir, cnxml, objects.items())
        validate_cnxml(cnxml)
        return "Google Document"

    @classmethod
    def get_gdoc_resource(klass, gdocs_resource_id, gdocs_access_token=None):
        http = httplib2.Http()
        if gdocs_access_token is not None:
            credentials = AccessTokenCredentials(gdocs_access_token, 'remix-client')
            credentials.authorize(http)
        drive = build('drive', 'v2', http=http)

        # Get the html version of the file
        md = drive.files().get(fileId=gdocs_resource_id).execute()
        uri = md['exportLinks']['text/html']

        resp, content = drive._http.request(uri)
        return resp, content, md['title']

class PresentationProcessor(BaseFormProcessor):
    def __init__(self, request, form):
        super(PresentationProcessor, self).__init__(request)
        self.set_source('presentation')
        self.set_target('new')
        ufname = form.data['upload_file'].filename.replace(os.sep, '_')
        self.original_filename = os.path.join(self.save_dir, ufname)
        self.request.session['filename'] = form.data['upload_file'].filename

        self.username = self.request.session['username']
        self.uploaded_filename = \
            form.data['upload_file'].filename.replace(os.sep, '_')
        self.original_filename = \
            os.path.join(self.save_dir, self.uploaded_filename)
    
    def create_save_dir(self, request):
        return create_save_dir(request, registry_key='slideshare_import_dir')
    
    def save_original_file(self, filename, input_file):
        saved_file = open(filename, 'wb')
        shutil.copyfileobj(input_file, saved_file)
        saved_file.close()

    def process(self, form):
        try:
            LOG.info("Inside presentation form")
            zipped_filepath = os.path.join(self.save_dir, "cnxupload.zip")
            LOG.info("Zipped filepath", zipped_filepath)
            self.request.session['userfilepath'] = zipped_filepath
            zip_archive = zipfile.ZipFile(zipped_filepath, 'w')
            zip_archive.write(self.original_filename, self.uploaded_filename)
            zip_archive.close()
            self.request.session['uploaded_filename'] = self.uploaded_filename
            self.request.session['original_filename'] = self.original_filename
            LOG.info("Original filename ", self.original_filename)
            self.request.session['title'] = self.uploaded_filename.split(".")[0]
            metadata = {}
            metadata['dcterms:title'] = self.uploaded_filename.split(".")[0]
            cnxml_now_string = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            cnxml = self.slide_importer_cnxml(cnxml_now_string, self.username)
            self.request.session['cnxml'] = cnxml

            # do a little metadata cleanup before we go to the metadata view
            for key in metadata.keys():
                if metadata[key] == '':
                    del metadata[key]
            self.request.session['metadata'] = metadata

        except ConversionError as e:
            return render_conversionerror(self.request, e.msg)

        except Exception:
            tb = traceback.format_exc()
            self.write_traceback_to_zipfile(tb, form)
            templatePath = 'templates/error.pt'
            response = {'traceback': tb}
            if('title' in self.request.session):
                del self.request.session['title']
            return render_to_response(templatePath, response, request=self.request)

        self.request.session.flash(self.message)
        return HTTPFound(location=self.request.route_url(self.nextStep()))

    def slide_importer_cnxml(self, now_string, username):
        config = load_config(self.request)
        filepath = config['slide_importer_cnxml_file'] 
        with open(filepath, 'rb') as cnxmlfile:
            content = cnxmlfile.read()
        return content % (now_string,
                          username,
                          username,
                          username,
                          username)

class URLProcessor(BaseFormProcessor):
    
    def __init__(self, request):
        super(URLProcessor, self).__init__(request)
        self.set_source('url')
        self.set_target('new')

    def process(self, form):
        try:
            url = form.data['url_text']

            # Build a regex for Google Docs URLs
            regex = re.compile(
                "^https:\/\/docs\.google\.com\/.*document\/[^\/]\/([^\/]+)\/")
            r = regex.search(url)

            # Take special action for Google Docs URLs
            if r is not None:
                gdocs_resource_id = r.groups()[0]
                http = httplib2.Http()
                http.follow_redirects = False
                try:
                    resp, html = http.request(
                        'https://docs.google.com/document/d/%s/export?format=html&confirm=no_antivirus' % gdocs_resource_id)
                except HttpError:
                    pass
                else:
                    # Check that status was OK, google docs sends a redirect to a login
                    # page if not.
                    if resp.status / 100 == 2:
                        # Get the title
                        title = etree.fromstring(html,
                            etree.HTMLParser()).xpath(
                            '/html/head/title/text()')[0] or \
                            'Untitled Google Document'

                        # Process it
                        P = GoogleDocProcessor(self.request)
                        return P.process_gdocs_resource(html, title, form)
                self.request.session.flash('Failed to convert google document')
                return HTTPFound(location=self.request.route_url('choose'))
            else:
                # download html:
                # Simple urlopen() will fail on mediawiki websites eg. Wikipedia!
                import_opener = urllib2.build_opener()
                import_opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                import_request = import_opener.open(url)
                html = import_request.read()

                # transformation
                cnxml, objects, html_title = htmlsoup_to_cnxml(
                        html, bDownloadImages=True, base_or_source_url=url)
                self.request.session['title'] = html_title

                cnxml = clean_cnxml(cnxml)
                save_cnxml(self.save_dir, cnxml, objects.items())

                # Keep the info we need for next uploads.  Note that
                # this might kill the ability to do multiple tabs in
                # parallel, unless it gets offloaded onto the form
                # again.
                self.request.session['filename'] = "HTML Document"

                validate_cnxml(cnxml)

        except ConversionError as e:
            return render_conversionerror(self.request, e.msg)

        except Exception:
            tb = traceback.format_exc()
            self.write_traceback_to_zipfile(tb, form)
            templatePath = 'templates/error.pt'
            response = {'traceback': tb}
            if('title' in self.request.session):
                del self.request.session['title']
            return render_to_response(templatePath, response, request=self.request)

        self.request.session.flash(self.message)
        return HTTPFound(location=self.request.route_url(self.nextStep()))
