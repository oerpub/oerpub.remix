from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings

def main(global_config, **settings):
    """
    This function returns a Pyramid WSGI application.
    """
    my_session_factory = session_factory_from_settings(settings)

    config = Configurator(settings=settings,
                          session_factory = my_session_factory)

    config.add_route('admin_config', '/config')
    config.add_route('login', '/')
    config.add_route('cnxlogin', '/cnxlogin')
    config.add_route('choose', '/choose')
    config.add_route('preview', '/preview')
    config.add_route('preview_header', '/preview_header')
    config.add_route('preview_body', '/preview_body')
    config.add_route('cnxml', '/cnxml')
    config.add_route('metadata', '/metadata')
    config.add_route('summary', '/summary')
    config.add_route('logout', '/logout')
    config.add_route('change_workspace', '/change_workspace')
    
    # every other add_route declaration should come
    # before this one, as it will, by default, catch all requests
    config.add_route('catchall_static', '/preview_css/*subpath', 'oerpub.rhaptoslabs.swordpushweb.static.static_view')

    config.add_static_view(
        'static',
        'oerpub.rhaptoslabs.swordpushweb:static',
        cache_max_age=3600)

    config.add_static_view(
        'static/external/codemirror2',
        'oerpub.rhaptoslabs.swordpushweb:codemirror',
        cache_max_age=3600)

    config.add_static_view(
        'transforms',
        'oerpub.rhaptoslabs.swordpushweb:transforms',
        cache_max_age=0)

    config.add_subscriber(
        '.subscribers.add_base_template',
        'pyramid.events.BeforeRender')

    config.scan()

    return config.make_wsgi_app()
