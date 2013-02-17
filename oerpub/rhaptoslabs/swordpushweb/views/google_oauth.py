import MySQLdb as mdb

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

from oerpub.rhaptoslabs.slideimporter.google_presentations import (
    GooglePresentationUploader,
    GoogleOAuth)

@view_config(route_name='google_oauth')
def google_oauth_callback(request):
    url = request.host_url + request.path_qs
    url =  url.replace('%2F','/')
    if not request.session.has_key('saved_request_token'):
        return HTTPFound(location = '/google_oauth')
    oauth = GoogleOAuth(request_token = request.session['saved_request_token'])
    oauth.authorize_request_token(request.session['saved_request_token'],url)
    oauth.get_access_token()
    session = request.session
    connection = mdb.connect('localhost', 'root',  'fedora', 'cnx_oerpub_oauth');
    oauth_token =  oauth.get_token_key()
    oauth_secret = oauth.get_token_secret()
    query = "INSERT INTO user(username,email,oauth_token,oauth_secret) VALUES("+"'"+session['username']+"'"+","+"'test@gmail.com'"+","+"'"+oauth_token+"'"+","+"'"+oauth_secret+"'"+")"
    with connection:
        cursor = connection.cursor()
        cursor.execute(query)
    connection.close()
    guploader = GooglePresentationUploader()
    guploader.authentincate_client_with_oauth2(oauth_token,oauth_secret)
    upload_to_gdocs = guploader.upload(session['original-file-path'])
    guploader.get_first_revision_feed()
    guploader.publish_presentation_on_web()
    resource_id = guploader.get_resource_id().split(':')[1]
    session['google-resource-id'] = resource_id
    if session.has_key('original-file-location'):
        del session['original-file-location']
    raise HTTPFound(location=request.route_url('enhance'))
