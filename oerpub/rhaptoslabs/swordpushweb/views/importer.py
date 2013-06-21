import formencode
from pyramid_simpleform import Form
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid_simpleform.renderers import FormRenderer

from oerpub.rhaptoslabs.slideimporter.slideshare import (
    upload_to_slideshare,
    get_details,
    get_slideshow_download_url,
    get_transcript,
    fetch_slideshow_status)
from oerpub.rhaptoslabs.slideimporter.google_presentations import (
    GooglePresentationUploader,
    GoogleOAuth)

from utils import check_login

class ImporterChoiceSchema(formencode.Schema):
    allow_extra_fields = True
    upload_to_ss = formencode.validators.String()
    upload_to_google = formencode.validators.String()
    #introductory_paragraphs = formencode.validators.String()

@view_config(route_name='importer',renderer='templates/importer.pt')
def return_slideshare_upload_form(request):
    check_login(request)
    session = request.session
    redirect_to_google_oauth = False

    form = Form(request, schema=ImporterChoiceSchema)
    response = {'form':FormRenderer(form)}
    username = session['login'].username
    if form.validate():
        original_filename = session['original_filename']
        slideshow_id = None
        if form.data['importer'] == 'slideshare':
            slideshow_id = upload_to_slideshare("saketkc", original_filename)
            session['slideshare_id'] = slideshow_id

        if form.data['importer'] == 'google':
            if session.has_key('slideshare_oauth'):
                # RETURNING USER
                redirect_to_google_oauth = False
                oauth_token = session['slideshare_oauth']["oauth_token"]
                oauth_secret = session['slideshare_oauth']["oauth_secret"]
                guploader = GooglePresentationUploader()
                guploader.authentincate_client_with_oauth2(oauth_token,oauth_secret)
                guploader.upload(original_filename)
                guploader.get_first_revision_feed()
                guploader.publish_presentation_on_web()
                resource_id = guploader.get_resource_id().split(':')[1]
                session['google-resource-id'] = resource_id
                print "UPLOADING TO GOOGLE"
            else:
                print "NEW USER"
                redirect_to_google_oauth = True
                session['original-file-path'] = original_filename

        uploaded_filename = session['uploaded_filename']
        if slideshow_id is not None:
            slideshare_details = get_details(slideshow_id)
        cnxml = """\
<featured-links>
  <!-- WARNING! The 'featured-links' section is read only. Do not edit below.
       Changes to the links section in the source will not be saved. -->
    <link-group type="supplemental">
      <link url="""+ "\"" + uploaded_filename + "\""+""" strength="3">Download the original slides in PPT format</link>"""
        if slideshow_id is not None:
            cnxml += """<link url="""+ "\"" + get_slideshow_download_url(slideshare_details) + "\"" +""" strength="2">SlideShare PPT Download Link</link>"""
        cnxml += """\
    </link-group>
  <!-- WARNING! The 'featured-links' section is read only. Do not edit above.
       Changes to the links section in the source will not be saved. -->
</featured-links>"""
        session['cnxml'] += cnxml

        if redirect_to_google_oauth:
            raise HTTPFound(location=request.route_url('google_oauth'))
        raise HTTPFound(location=request.route_url('enhance'))
    return {'form' : FormRenderer(form),'conversion_flag': False, 'oembed': False}
