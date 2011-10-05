from pyramid.config import Configurator

def main(global_config, **settings):
    """
    This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)

    config.add_view('oerpub.rhaptoslabs.swordpushweb.views.my_view',
                    renderer='oerpub.rhaptoslabs.swordpushweb:templates/login.pt')
    config.add_view('oerpub.rhaptoslabs.swordpushweb.views.auth_view',
                    name='auth',
                    renderer='oerpub.rhaptoslabs.swordpushweb:templates/upload.pt')
    config.add_view('oerpub.rhaptoslabs.swordpushweb.views.upload_view',
                    name='upload',
                    renderer='oerpub.rhaptoslabs.swordpushweb:templates/upload.pt')

    config.add_static_view('static', 'oerpub.rhaptoslabs.swordpushweb:static', cache_max_age=3600)

    config.add_subscriber('oerpub.rhaptoslabs.swordpushweb.subscribers.add_base_template',
                          'pyramid.events.BeforeRender')

    return config.make_wsgi_app()
