from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings

def main(global_config, **settings):
    """
    This function returns a Pyramid WSGI application.
    """
    my_session_factory = session_factory_from_settings(settings)

    config = Configurator(settings=settings,
                          session_factory = my_session_factory)

    config.add_route('upload', '/upload')
    config.add_route('auth', '/auth')
    config.add_route('logout', '/logout')
    config.add_route('main', '/')

    config.add_static_view(
        'static',
        'oerpub.rhaptoslabs.swordpushweb:static',
        cache_max_age=3600)

    config.add_subscriber(
        '.subscribers.add_base_template',
        'pyramid.events.BeforeRender')

    config.scan()

    return config.make_wsgi_app()
