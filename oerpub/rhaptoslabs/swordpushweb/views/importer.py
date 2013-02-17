import formencode
import MySQLdb as mdb

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
    if session.has_key('original-file-location'):
        del session['original-file-location']
    form = Form(request, schema=ImporterChoiceSchema)
    response = {'form':FormRenderer(form)}
    validate_form = form.validate()
    if validate_form:
        original_filename = session['original_filename']
        upload_to_google = form.data['upload_to_google']
        upload_to_ss = form.data['upload_to_ss']
        username = session['username']
        if (upload_to_ss=="true"):

            slideshow_id = upload_to_slideshare("saketkc",original_filename)
            session['slideshare_id'] = slideshow_id
        if (upload_to_google == "true"):
            if is_returning_google_user(username):
                print "RETURNING USER"
                redirect_to_google_oauth = False
                oauth_token_and_secret = get_oauth_token_and_secret(username)
                oauth_token = oauth_token_and_secret["oauth_token"]
                oauth_secret = oauth_token_and_secret["oauth_secret"]
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
        else:
            print "NO GOOGLE FOUND"
        username = session['username']
        uploaded_filename = session['uploaded_filename']
        slideshare_details = get_details(slideshow_id)
        slideshare_download_url = get_slideshow_download_url(slideshare_details)
        session['transcript'] = get_transcript(slideshare_details)
        cnxml = """<featured-links>
  <!-- WARNING! The 'featured-links' section is read only. Do not edit below.
       Changes to the links section in the source will not be saved. -->
    <link-group type="supplemental">
      <link url="""+ "\"" + uploaded_filename + "\""+""" strength="3">Download the original slides in PPT format</link>
      <link url="""+ "\"" +slideshare_download_url + "\"" +""" strength="2">SlideShare PPT Download Link</link>
    </link-group>
  <!-- WARNING! The 'featured-links' section is read only. Do not edit above.
       Changes to the links section in the source will not be saved. -->
</featured-links>"""
        session['cnxml'] += cnxml



        #print deposit_receipt.metadata #.get("dcterms_title")
        if redirect_to_google_oauth:
            raise HTTPFound(location=request.route_url('google_oauth'))
        raise HTTPFound(location=request.route_url('enhance'))
    return {'form' : FormRenderer(form),'conversion_flag': False, 'oembed': False}


def is_returning_google_user(username):
    connection = mdb.connect('localhost', 'root', 'fedora', 'cnx_oerpub_oauth')
    query = "SELECT * FROM user WHERE username='"+username+"'"
    print query
    numrows=0
    with connection:
        cursor = connection.cursor()
        cursor.execute(query)
        numrows = int(cursor.rowcount)
    connection.close()
    if numrows == 0:
        return False
    else :
        return True


def get_oauth_token_and_secret(username):
    try:
        connection = mdb.connect('localhost', 'root',  'fedora', 'cnx_oerpub_oauth');
        with connection:
            cursor = connection.cursor()
            cursor.execute("SELECT oauth_token,oauth_secret FROM user WHERE username='"+username+"'")
            row = cursor.fetchone()
            return {"oauth_token": row[0],"oauth_secret":row[1]}
    except mdb.Error, e:
        print e
