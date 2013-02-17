from pyramid.view import view_config
from pyramid.renderers import render_to_response

from utils import check_login, load_config

@view_config(route_name='cnxlogin')
def cnxlogin_view(request):
    check_login(request)

    config = load_config(request)
    login_url = config['login_url']

    templatePath = 'templates/cnxlogin.pt'
    response = {
        'username': request.session['username'],
        'password': request.session['password'],
        'login_url': login_url,
    }
    return render_to_response(templatePath, response, request=request)


