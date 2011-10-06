import oerpub.rhaptoslabs.sword1cnx as swordcnx
from languages import languages

def my_view(request):
    return { 'project':'SwordPush' }


def auth_view(request):
    """
    Handle authentication (login) requests.
    """
    # TODO: check credentials against Connexions and ask for login
    # again if failed.

    serviceDocument = request.params['serviceDocument']

    # Encode authentication information
    import base64
    username = request.params['username']
    password = request.params['password']
    digest = base64.b64encode(username + ':' + password)

    # Authenticate to Connexions
    conn = swordcnx.Connection(serviceDocument,
                               user_name=username,
                               user_pass=password,
                               download_service_document=True)

    # Get available collections from SWORD service document
    swordCollections = swordcnx.parse_service_document(conn.sd)


    return {
        'serviceDocument': serviceDocument,
        'credentials': digest,
        'swordCollections': swordCollections,
        'url': '',
        'title': '',
        'keepTitle': False,
        'summary': '',
        'keepSummary': False,
        'keywords': '',
        'keepKeywords': True,
        'languages': languages,
        'language': 'en',
    }

def upload_view(request):
    """
    Handle SWORD uploads POSTed from a form.
    """

    inputs = request.params

    # Decode authentication information
    import base64
    authString = base64.b64decode(inputs['credentials'])
    pos = authString.find(':')
    username = authString[:pos]
    password = authString[pos+1:]
    assert base64.b64encode(username + ':' + password) == inputs['credentials']

    conn = swordcnx.Connection(inputs['serviceDocument'],
                               user_name=username,
                               user_pass=password,
                               download_service_document=True)

    # Get available collections from SWORD service document
    swordCollections = swordcnx.parse_service_document(conn.sd)

    # Parse form elements
    import os
    filesToUpload = {}
    for key in ['file1','file2','file3']:
        if hasattr(inputs[key], 'file'):
            filesToUpload[os.path.basename(inputs[key].filename)] = inputs[key].file

    # Send zip file to Connexions through SWORD interface
    conn = swordcnx.Connection(inputs['url'],
                               user_name=username, user_pass=password,
                               download_service_document=False)
    response = swordcnx.upload_multipart(
        conn, inputs['title'], inputs['summary'], inputs['language'],
        inputs['keywords'].split("\n"), filesToUpload)

    return {
        'serviceDocument': inputs['serviceDocument'],
        'credentials': inputs['credentials'],
        'swordCollections': swordCollections,
        'url': inputs['url'],
        'title': inputs['title'] if inputs.get('keepTitle') else '',
        'keepTitle': inputs.get('keepTitle', False),
        'summary': inputs['summary'] if inputs.get('keepSummary') else '',
        'keepSummary': inputs.get('keepSummary', False),
        'keywords': inputs['keywords'] if inputs.get('keepKeywords') else '',
        'keepKeywords': inputs.get('keepKeywords', False),
        'languages': languages,
        'language': inputs['language'],
    }
