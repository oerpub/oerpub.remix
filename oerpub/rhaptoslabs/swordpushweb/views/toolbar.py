from pyramid.view import view_config

@view_config(name='toolbar', renderer='templates/toolbar.pt')
def toolbar(request):
    return {}
