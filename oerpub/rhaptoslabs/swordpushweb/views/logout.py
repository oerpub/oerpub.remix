from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound


@view_config(route_name='logout', renderer='templates/login.pt')
def logout_view(request):
    session = request.session
    session.invalidate()
    raise HTTPFound(location=request.route_url('login'))


