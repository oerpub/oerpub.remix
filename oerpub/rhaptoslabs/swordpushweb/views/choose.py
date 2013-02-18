import os
import re
import shutil
import zipfile
import urllib2
import datetime
import traceback
import formencode
import subprocess

from lxml import etree

from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
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
from oerpub.rhaptoslabs.swordpushweb.views.utils import (
    load_config,
    save_zip,
    clean_cnxml,
    save_cnxml,
    validate_cnxml,
    check_login,
    escape_system,
    add_directory_to_zip,
    render_conversionerror)
from oerpub.rhaptoslabs.swordpushweb.errors import ConversionError


class ModuleEditorSchema(formencode.Schema):
    allow_extra_fields = True
    newmodule = formencode.validators.Bool()
    existingmodule = formencode.validators.Bool()

class WordprocessorSchema(formencode.Schema):
    allow_extra_fields = True
    upload_file = formencode.validators.FieldStorageUploadConverter()

class GoogleDocsSchema(formencode.Schema):
    allow_extra_fields = True
    upload_url = formencode.validators.URL()

class URLSchema(formencode.Schema):
    allow_extra_fields = True
    upload_url = formencode.validators.URL()

class UploadSchema(formencode.Schema):
    allow_extra_fields = True
    upload_file = formencode.validators.FieldStorageUploadConverter()

class ImporterSchema(formencode.Schema):
    allow_extra_fields = True
    importer = formencode.validators.FieldStorageUploadConverter()
    #upload_to_ss = formencode.validators.String()
    #upload_to_google = formencode.validators.String()
    #introductory_paragraphs = formencode.validators.String()

class ZipOrLatexSchema(formencode.Schema):
    allow_extra_fields = True
    upload_file = formencode.validators.FieldStorageUploadConverter()


class Choose_Document_Source(BaseHelper):

    navigation_actions = {'next': '', 
                          'previous': '/',
                          'batch': ''}

    @view_config(route_name='choose')
    def generate_html_view(self):
        self.check_login()
        request = self.request
        session = request.session

        templatePath = 'templates/choose.pt'

        form = Form(self.request, schema=UploadSchema)
        neworexisting_form = Form(request, schema=ModuleEditorSchema)
        wordprocessor_form = Form(request, schema=WordprocessorSchema)
        googledocs_form = Form(request, schema=GoogleDocsSchema)
        url_form = Form(request, schema=URLSchema)
        presentationform = Form(request, schema=ImporterSchema)
        zip_or_latex_form = Form(request, schema=ZipOrLatexSchema)
        field_list = [('upload', 'File')]

        # clear the session
        if 'transformerror' in self.request.session:
            del self.request.session['transformerror']
        if 'title' in self.request.session:
            del self.request.session['title']

        # Check for successful form completion
        print form.all_errors()
        print presentationform.all_errors()

        if neworexisting_form.validate():
            return self._process_neworexisting_submit(request, neworexisting_form)
        elif wordprocessor_form.validate():
            self._process_wordprocessor_submit()
        elif googledocs_form.validate():
            self._process_googledocs_submit()
        elif url_form.validate():
            self._process_url_submit()
        elif presentationform.validate():
            self._process_presentationform_submit()
        elif zip_or_latex_form.validate():
            self._process_zip_or_latex_form()

        # First view or errors
        response = {
            'form': FormRenderer(form),
            'neworexisting_form': FormRenderer(neworexisting_form),
            'wordprocessor_form': FormRenderer(wordprocessor_form),
            'googledocs_form': FormRenderer(googledocs_form),
            'url_form': FormRenderer(url_form),
            'presentationform': FormRenderer(presentationform),
            'field_list': field_list,
            'view': self,
        }
        return render_to_response(templatePath, response, request=self.request)

    def getNextUrl(self):
        return ''

    def _process_neworexisting_submit(self, request, form):
        print 'process new or existing submit'
        processor = NewOrExistingModuleProcessor(request, form)
        return processor.process()
        result = ''
        if result:
            nextUrl = self.getNextUrl()


    def _process_wordprocessor_submit(self):
        print 'process wordprocessor submit'
    
    def _process_googledocs_submit(self):
        print 'process google doc submit'
    
    def _process_url_submit(self):
        print 'process URL submit'

    def _process_presentationform_submit(self):
        print 'process presentation submit'
    
    def _process_zip_or_latex_form(self):
        print 'process zip or latex submit'

    def process_gdoc_data(self, form, request, save_dir):
        gdocs_resource_id = form.data['gdocs_resource_id']
        gdocs_access_token = form.data['gdocs_access_token']

        form.data['gdocs_resource_id'] = None
        form.data['gdocs_access_token'] = None

        title, filename = self.process_gdocs_resource(
            save_dir, gdocs_resource_id)

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
                response = {'form': FormRenderer(form),}
                return render_to_response(self.templatePath,
                                          response,
                                          request=request)

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
                command = None
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
                    if command == None:
                        raise ConversionError("%s not found" %
                                              original_filename)
                    else:
                        raise ConversionError(
                            "%s not found because command \"%s\" failed" %
                            (odt_filename,command) )
            
            # Convert and save all the resulting files.

            tree, files, errors = transform(odt_filename)
            cnxml = clean_cnxml(etree.tostring(tree))

            save_cnxml(save_dir, cnxml, files.items())

            # now validate with jing
            validate_cnxml(cnxml)

    def process_presentation_data(self, request, form, session):
        print "Inside presentation form"
        now_string = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        cnxml_now_string = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        temp_dir_name = '%s-%s' % (request.session['username'], now_string)
        save_dir = os.path.join(
            request.registry.settings['slideshare_import_dir'],
            temp_dir_name
        )
        os.mkdir(save_dir)
        uploaded_filename = form.data['importer'].filename.replace(os.sep, '_')
        original_filename = os.path.join(save_dir, uploaded_filename)
        saved_file = open(original_filename, 'wb')
        input_file = form.data['importer'].file
        shutil.copyfileobj(input_file, saved_file)
        saved_file.close()
        input_file.close()
        username = session['username']

        zipped_filepath = os.path.join(save_dir,"cnxupload.zip")
        print "Ziiped filepath",zipped_filepath
        session['userfilepath'] = zipped_filepath
        zip_archive = zipfile.ZipFile(zipped_filepath, 'w')
        zip_archive.write(original_filename,uploaded_filename)
        zip_archive.close()
        session['uploaded_filename'] = uploaded_filename
        session['original_filename'] = original_filename
        print "Original filename ",original_filename
        username = session['username']
        #slideshare_details = get_details(slideshow_id)
        #slideshare_download_url = get_slideshow_download_url(slideshare_details)
        #session['transcript'] = get_transcript(slideshare_details)
        session['title'] = uploaded_filename.split(".")[0]
        metadata = {}
        metadata['dcterms:title'] = uploaded_filename.split(".")[0]
        cnxml = self.slide_importer_cnxml(cnxml_now_string, username)
        print cnxml
        session['cnxml'] = cnxml
        return HTTPFound(location=request.route_url('importer'))

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

class BaseFormProcessor(object):
    def __init__(self, request, form):
        self.request = request
        self.form = form
        self.message = 'The file was successfully converted.'
        self.source = 'undefined'
        self.temp_dir_name, self.save_dir = self.create_work_dir(self.request)
        self.upload_dir = self.temp_dir_name
        self.request.session['upload_dir'] = self.temp_dir_name

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

    def write_traceback_to_zipfile(self, traceback):
        # Record traceback

        # Get software version from git
        commit_hash = self.get_commit_hash()
        
        # get the path to the error zip file
        zip_filename = os.path.join(
            self.request.registry.settings['errors_dir'],
            self.temp_dir_name + '.zip'
        )

        # Zip up error report, form data, uploaded file (if any)  and
        # temporary transform directory
        zip_archive = zipfile.ZipFile(zip_filename, 'w')
        info = self.format_info(traceback, commit_hash, self.request, self.form)
        zip_archive.writestr("info.txt", info)

        basePath = self.request.registry.settings['transform_dir']
        add_directory_to_zip(self.temp_dir_name,
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

class NewOrExistingModuleProcessor(BaseFormProcessor):
    def process(self):
        try:
            if self.form.data.get('newmodule'):
                self.set_source('newemptymodule')
                # save empty cnxml and html files
                cnxml = self.empty_cnxml()
                files = []
                save_cnxml(self.save_dir, cnxml, files)
            
            elif self.form.data.get('existingmodule'):
                self.set_source('existingmodule')
                return HTTPFound(
                    location=self.request.route_url('choose-module'))

        except ConversionError as e:
            return render_conversionerror(self.request, e.msg)

        except Exception:
            tb = traceback.format_exc()
            self.write_traceback_to_zipfile(tb)
            templatePath = 'templates/error.pt'
            response = {'traceback': tb}
            if('title' in self.request.session):
                del self.request.session['title']
            return render_to_response(templatePath, response, request=self.request)

        self.request.session.flash(self.message)
        return HTTPFound(location=self.request.route_url('preview'))
        
    def empty_cnxml(self):
        config = load_config(self.request)
        filepath = config['blank_cnxml_file'] 
        with open(filepath, 'rb') as cnxmlfile:
            content = cnxmlfile.read()
        return content


"""
        elif form.validate():
            print "NORMAL FORM"
            try: # Catch-all exception block
                message = 'The file was successfully converted.'

                # Create a directory to do the conversions
                temp_dir_name, save_dir = self.create_work_dir(self.request)

                # Keep the info we need for next uploads.  Note that this
                # might kill the ability to do multiple tabs in parallel,
                # unless it gets offloaded onto the form again.
                self.request.session['upload_dir'] = temp_dir_name
                self.source = 'undefined'
                if form.data.get('newmodule'):
                    self.set_source('newemptymodule')
                    # save empty cnxml and html files
                    cnxml = self.empty_cnxml()
                    files = []
                    save_cnxml(save_dir, cnxml, files)
                
                elif form.data.get('existingmodule'):
                    self.set_source('existingmodule')
                    return HTTPFound(
                        location=self.request.route_url('choose-module'))

                elif form.data['upload'] is not None:
                    self.set_source('fileupload')
                    self.request.session['filename'] = form.data['upload'].filename
                    self.process_document_data(form, self.request, save_dir)

                # Google Docs Conversion
                # if we have a Google Docs ID and Access token.
                elif form.data.get('gdocs_resource_id'):
                    self.set_source('gdocupload')
                    self.process_gdoc_data(form, self.request, save_dir)

                # HTML URL Import:
                elif form.data.get('url_text'):
                    self.set_source('urlupload')
                    errors = self.process_url_data(form, self.request, save_dir)
                    if errors:
                        self.request['errors'] = errors
                        response = {'form': FormRenderer(form),
                                    'view': self, }
                        return render_to_response(
                            templatePath, response, request=self.request)

                # Office, CNXML-ZIP or LaTeX-ZIP file
                else:
                    self.set_source('cnxinputs')
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
        
        elif presentationform.validate():
            self.process_presentation_data(request, presentationform, session)
"""

