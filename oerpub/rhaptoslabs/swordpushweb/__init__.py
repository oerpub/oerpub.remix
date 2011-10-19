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
    config.add_route('preview', '/preview')
    config.add_route('metadata', '/metadata')
    config.add_route('summary', '/summary')
    config.add_route('roles', '/roles')
    config.add_route('logout', '/logout')
    config.add_route('main', '/')
    config.add_route('change_workspace', '/change_workspace')
    config.add_route('sword_treatment', '/sword_treatment')
    
    # every other add_route declaration should come
    # before this one, as it will, by default, catch all requests
    config.add_route('catchall_static', '/preview_css/*subpath', 'oerpub.rhaptoslabs.swordpushweb.static.static_view')

    config.add_static_view(
        'static',
        'oerpub.rhaptoslabs.swordpushweb:static',
        cache_max_age=3600)

    config.add_static_view(
        'transforms',
        'oerpub.rhaptoslabs.swordpushweb:transforms',
        cache_max_age=3600)

    config.add_subscriber(
        '.subscribers.add_base_template',
        'pyramid.events.BeforeRender')

    config.scan()

    return config.make_wsgi_app()
