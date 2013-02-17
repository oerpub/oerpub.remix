from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render_to_response
from pyramid_simpleform.renderers import FormRenderer

from oerpub.rhaptoslabs import sword2cnx

from oerpub.rhaptoslabs.swordpushweb import languages
from metadata import MetadataSchema
from utils import check_login, load_config

@view_config(route_name='updatecnx')
def update_cnx_metadata(request):
    """
    Handle update of metadata to cnx
    """
    check_login(request)
    templatePath = 'templates/update_metadata.pt'
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
    defaults = {}

    for role in ['authors', 'maintainers', 'copyright', 'editors', 'translators']:
        defaults[role] = ','.join(config['metadata'][role]).replace('_USER_', session['username'])
        config['metadata'][role] = ', '.join(config['metadata'][role]).replace('_USER_', session['username'])

    if 'title' in session:
        print('TITLE '+session['title']+' in session')
        defaults['title'] = session['title']
        config['metadata']['title'] = session['title']

    form = Form(request,
                schema=MetadataSchema,
                defaults=defaults
                )

    # Check for successful form completion
    if form.validate():
        for field_name in remember_fields:
            if form.data['keep_%s' % field_name]:
                session[field_name] = form.data[field_name]
            else:
                if field_name in session:
                    del(session[field_name])

        metadata = {}
        metadata['dcterms:title'] = form.data['title'] if form.data['title'] \
                                    else session['filename']
        metadata_entry = sword2cnx.MetaData(metadata)
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
        conn = sword2cnx.Connection("http://cnx.org/sword/servicedocument",
                                    user_name=session['username'],
                                    user_pass=session['password'],
                                    always_authenticate=True,
                                    download_service_document=True)
        update = conn.update(edit_iri=session['edit_iri'],metadata_entry = metadata_entry,in_progress=True,metadata_relevant=True)
        metadata={}
        metadata['dcterms:title'] = form.data['title'] if form.data['title'] \
                                    else session['filename']
        metadata['dcterms:abstract'] = form.data['summary'].strip()
        metadata['dcterms:language'] = form.data['language']
        metadata['dcterms:subject'] = [i.strip() for i in
                                       form.data['keywords'].splitlines()
                                       if i.strip()]
        metadata['oerdc:oer-subject'] = form.data['subject']
        for key in metadata.keys():
            if metadata[key] == '':
                del metadata[key]
        add = conn.update_metadata_for_resource(edit_iri=session['edit_iri'],metadata_entry = metadata_entry,in_progress=True)
        metadata['oerdc:analyticsCode'] = form.data['google_code'].strip()
        for key in metadata.keys():
            if metadata[key] == '':
                del metadata[key]
        metadata_entry = sword2cnx.MetaData(metadata)
        add = conn.update(edit_iri=session['edit_iri'],metadata_entry = metadata_entry,in_progress=True)
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
