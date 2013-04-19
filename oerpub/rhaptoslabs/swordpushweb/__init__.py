from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings

from .interfaces import IWorkflowSteps
from .provider import WorkflowStepsUtility

def main(global_config, **settings):
    """
    This function returns a Pyramid WSGI application.
    """
    my_session_factory = session_factory_from_settings(settings)

    config = Configurator(settings=settings,
                          session_factory = my_session_factory)
    
    add_routes(config)
    add_static_resources(config)
    add_subscribers(config)
    register_utilities(config)

    # Configure Velruse
    config.include('oerpub.rhaptoslabs.swordpushweb.google')
    config.add_google_oauth2_login_from_settings()

    config.scan()
    return config.make_wsgi_app()


def add_routes(config):
    config.add_route('admin_config', '/config')
    config.add_route('login', '/')
    config.add_route('cnxlogin', '/cnxlogin')
    config.add_route('choose', '/choose')
    config.add_route('preview', '/preview')
    config.add_route('preview_save', '/preview_save')
    config.add_route('cnxml', '/cnxml')
    config.add_route('metadata', '/metadata')
    config.add_route('summary', '/summary')
    config.add_route('logout', '/logout')
    config.add_route('importer', '/importer')
    config.add_route('google_oauth', '/google_oauth')
    config.add_route('module_association', '/module_association')
    config.add_route('modules_list', '/modules_list')
    config.add_route('download_zip', '/download_zip')
    config.add_route('oauth2callback', '/oauth2callback')
    config.add_route('choose-module', '/choose-module')
    config.add_route('upload_dnd', '/upload_dnd')
    config.add_route('updatecnx', '/updatecnx')
    config.add_route('enhance', '/enhance')
    config.add_route('json_get_source_from_session', '/json_get_source_from_session')
    config.add_route('json_get_target_from_session', '/json_get_target_from_session')
    config.add_route('json_set_source_on_session', '/json_set_source_on_session')
    config.add_route('json_set_target_on_session', '/json_set_target_on_session')

    # every other add_route declaration should come
    # before this one, as it will, by default, catch all requests
    config.add_route('catchall_static', '/preview_css/*subpath', 'oerpub.rhaptoslabs.swordpushweb.static.static_view')


def add_static_resources(config):
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

def add_subscribers(config):
    config.add_subscriber(
        '.subscribers.add_base_template',
        'pyramid.events.BeforeRender')

    config.add_subscriber(
        '.subscribers.add_provider',
        'pyramid.events.BeforeRender')

    config.add_subscriber(
        '.subscribers.add_utils',
        'pyramid.events.BeforeRender')

def register_utilities(config):
    config.registry.registerUtility(WorkflowStepsUtility(), IWorkflowSteps)
