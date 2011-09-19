from pyramid.config import Configurator

def main(global_config, **settings):
    """
    This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)

    config.add_view('swordpush.views.my_view',
                    renderer='swordpush:templates/login.pt')
    config.add_view('swordpush.views.auth_view',
                    name='auth',
                    renderer='swordpush:templates/upload.pt')
    config.add_view('swordpush.views.upload_view',
                    name='upload',
                    renderer='swordpush:templates/upload.pt')

    config.add_static_view('static', 'swordpush:static', cache_max_age=3600)

    return config.make_wsgi_app()
