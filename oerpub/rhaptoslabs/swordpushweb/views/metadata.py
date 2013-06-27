import os
import types
import formencode
import peppercorn

from pyramid.decorator import reify
from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid.renderers import render_to_response
from pyramid_simpleform.renderers import FormRenderer
from pyramid.httpexceptions import HTTPFound

from oerpub.rhaptoslabs.sword2cnx import sword2cnx
from oerpub.rhaptoslabs.swordpushweb.languages import languages

from choose import save_cnxml
from utils import ZIP_PACKAGING, create_module_in_2_steps
from utils import load_config, build_featured_links
from utils import make_zip
from helpers import BaseHelper

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
            [(i['href'], i['title']) for i in self.session['login'].collections]

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
    
    def _get_metadata(self, form, session):
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
        return metadata

    def get_metadata_entry(self, form, session):
        metadata = self._get_metadata(form, session)

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

    def create_module_with_atompub_xml(self, conn, collection_iri, entry):
        dr = conn.create(col_iri = collection_iri,
                         metadata_entry = entry,
                         in_progress = True)
        return dr

    def update_module(self, save_dir, connection, metadata, target_module_url):
        zip_file = make_zip(save_dir, self.request.session['login'].files)
        
        # We cannot be sure whether the '/sword' will be there or not,
        # so we remove it, which works fine even if it is not there.
        # This gives us a predictable base to start from.
        base_url = target_module_url.strip('/sword')
        # Now we add it back, but only for the edit-iri.
        edit_iri = base_url + '/sword'
        # The editmedia-iri does not want '/sword' in it.
        edit_media_iri = base_url + '/editmedia'

        deposit_receipt = connection.update(
            metadata_entry = metadata,
            payload = zip_file,
            filename = 'upload.zip',
            mimetype = 'application/zip',
            packaging = ZIP_PACKAGING,
            edit_iri = edit_iri,
            edit_media_iri = edit_media_iri,
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
        return session.get('title', metadata.get('dcterms:title'))

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
    def process(self):
        """
        Handle metadata adding and uploads
        """
        super(Metadata_View, self)._process()
        request = self.request
        defaults = self.defaults
        form = Form(request,
                    schema=MetadataSchema,
                    defaults=defaults
                   )

        errors = self.do_transition(form)
        if request.params.get('btn-restart'):
            # If user clicked the restart button (this only happens if he is
            # anonymous), send him to the choose-page. Disable expert mode.
            request.response.set_cookie('oerpushweb.expertmode', 'false')
            return HTTPFound(
                location=request.route_url('choose')+"?restart=1",
                headers=request.response.headers)

        return self.navigate(errors, form)

    def do_transition(self, form):
        errors = {}
        session = self.session
        request = self.request
        workspaces = self.workspaces

        # If the user cannot upload, then a workspace isn't required. This
        # allows the form to otherwise validate.
        if not self.request.session['login'].canUploadModule:
            form.schema.fields['workspace'].not_empty = False

        # Check for successful form completion
        if form and form.validate():
            # Find what the user actually wanted to do.
            # This is important since we don't want to upload the module to cnx
            # if the user clicked on the back button.

            action = 'back'
            if self.request.params.get('btn-forward'):
                action = 'forward'
            elif self.request.params.get('btn-restart'):
                action = 'restart'

            if action in ('forward', 'restart'):
                # Reconstruct the path to the saved files
                save_dir = request.session['login'].saveDir
                title = form.data['title']

                metadata = {}
                metadata.update(request.session['login'].metadata)
                metadata.update(self._get_metadata(form, session))
                metadata['featured_link_groups'] = \
                    self.get_raw_featured_links(request)

                # update the cnxml
                cnxml = open(os.path.join(save_dir, 'index.cnxml'), 'r').read()
                save_cnxml(save_dir, cnxml, title=title, metadata=metadata)

                if action == 'forward':
                    self.set_selected_workspace(form.data['workspace'])
                    self.update_session(session, self.remember_fields, form)

                    # Create a connection to the sword service
                    conn = self.get_connection()

                    # Send zip file to Connexions through SWORD interface
                    files = self.request.session['login'].files
                    zip_file = make_zip(save_dir, files)

                    target_module_url = session['login'].module_url
                    import pdb; pdb.set_trace()
                    metadata_entry = self.get_metadata_entry(form, session)
                    if target_module_url:
                        # this is an update not a create
                        deposit_receipt = self.update_module(
                            save_dir, conn, metadata_entry, target_module_url)
                    else:
                        # this is a workaround until I can determine why the 
                        # featured links don't upload correcly with a multipart
                        # upload during module creation. See redmine issue 40
                        # TODO:
                        # Fix me properly!
                        if self.featured_links:
                            deposit_receipt = create_module_in_2_steps(
                                form, conn, metadata_entry, zip_file)
                        else:
                            deposit_receipt = self.create_module(
                                form, conn, metadata_entry, zip_file)

                    # Remember to which workspace we submitted
                    session['deposit_workspace'] = workspaces[[x[0] for x in workspaces].index(form.data['workspace'])][1]

                    # The deposit receipt cannot be pickled, so we pickle the xml
                    session['deposit_receipt'] = deposit_receipt.to_xml()
        else:
            errors.update(form.errors)
            return errors

    def navigate(self, errors=None, form=None):
        # See if this was a plain navigation attempt
        view = super(Metadata_View, self)._navigate(errors, form)
        if view:
            return view 
        
        # It was not, let's prepare the default view.
        session = self.session
        request = self.request
        config = self.config
        workspaces = self.workspaces
        subjects = self.subjects
        field_list = self.field_list
        target_module_url = session['login'].module_url
        target_metadata = session['login'].metadata

        metadata = config['metadata']
        username = session['login'].username
        password = session['login'].password
        if target_module_url:
            if target_module_url.endswith('/sword'):
                dr_url = target_module_url
            else:
                dr_url = target_module_url + '/sword'
            if target_metadata is not None:
                metadata.update(target_metadata)
        else:
            for role in ['authors', 'maintainers', 'copyright', 'editors', 'translators']:
                self.defaults[role] = ','.join(
                    self.config['metadata'][role]).replace('_USER_', username)

                self.config['metadata'][role] = ', '.join(
                    self.config['metadata'][role]).replace('_USER_', username)
                
                self.defaults['language'] = \
                    self.config['metadata'].get('language', u'en')

        selected_workspace = self.get_selected_workspace()
        workspace_title = self.get_selected_workspace_title()
        response =  {
            'form': FormRenderer(form),
            'field_list': field_list,
            'workspaces': workspaces,
            'selected_workspace': selected_workspace,
            'workspace_title': workspace_title,
            'languages': languages,
            'subjects': subjects,
            'config': config,
            'macros': self.macro_renderer,
            'metadata': metadata,
            'session': session,
            'view': self,
        }
        # Enable expert mode when anonymous
        if not self.request.session['login'].canUploadModule:
            request.response.set_cookie('oerpushweb.expertmode', 'true')
        return render_to_response(self.templatePath, response, request=request)

    @reify
    def back_step_label(self):
        return "&laquo; Back: Return to preview page"
    
    @reify
    def next_step_label(self):
        return "Next: Upload module to Connexions&raquo;" 

    @reify
    def next_step_title(self):
        return "Click 'Finish' to add the module as edited to the designated work area. Further steps are required before the module can be published in the Connexions repository."

    @reify
    def back_step_title(self):
        return "Return to the preview page"

    def get_next_action(self, *args, **kwargs):
        """ If we don't have upload rights, there is no next action. """
        if self.request.session['login'].canUploadModule:
            return super(Metadata_View, self).get_next_action(
                *args, **kwargs)
        return None
