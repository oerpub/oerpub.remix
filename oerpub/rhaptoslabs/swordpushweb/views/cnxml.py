import os
import zipfile
import formencode

from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid_simpleform.renderers import FormRenderer
from pyramid.httpexceptions import HTTPFound

from choose import save_cnxml, validate_cnxml
from utils import check_login, get_files_from_zipfile, clean_cnxml


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
