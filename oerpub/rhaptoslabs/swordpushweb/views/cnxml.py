import os
import zipfile
import formencode

from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid_simpleform.renderers import FormRenderer
from pyramid.httpexceptions import HTTPFound, HTTPNotFound

from utils import save_cnxml, validate_cnxml
from utils import check_login, clean_cnxml


class CnxmlSchema(formencode.Schema):
    allow_extra_fields = True
    cnxml = formencode.validators.String(not_empty=True)


@view_config(route_name='cnxml', renderer='templates/cnxml_editor.pt')
def cnxml_view(request):
    check_login(request)
    form = Form(request, schema=CnxmlSchema)
    save_dir = request.session['login'].saveDir
    cnxml_filename = os.path.join(save_dir, 'index.cnxml')
    transformerror = request.session.get('transformerror')

    # Check for successful form completion
    if 'cnxml' in request.POST and form.validate():
        cnxml = form.data['cnxml']

        # Keep sure we use the standard python ascii string and encode Unicode to xml character mappings
        if isinstance(cnxml, unicode):
            cnxml = cnxml.encode('ascii', 'xmlcharrefreplace')        

        try:
            save_cnxml(save_dir, cnxml)
            validate_cnxml(cnxml)
        except ConversionError as e:
            return render_conversionerror(request, e.msg)

        # Return to preview
        return HTTPFound(location=request.route_url('preview'), request=request)

    # Read CNXML
    try:
        with open(cnxml_filename, 'rt') as fp:
            cnxml = fp.read()
    except IOError:
        raise HTTPNotFound('index.cnxml not found')

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
