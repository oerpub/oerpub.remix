from pyramid.renderers import get_renderer
from .provider import Provider
from .interfaces import IWorkflowSteps

def add_base_template(event):
    """
    Expose the base template as per the Pyramid cookbook:

    https://docs.pylonsproject.org/projects/pyramid_cookbook/dev/templates.html#using-a-beforerender-event-to-expose-chameleon-base-template
    """
    base = get_renderer('templates/base.pt').implementation()
    event.update({'base': base})
    base = get_renderer('templates/base_bare.pt').implementation()
    event.update({'basebare': base})

def add_provider(event):
    """
    Add a provider() callable whereby views can be used inside other
    views/templates, much like zope/plone providers. """
    provider = Provider(event['context'], event['request'])
    event['provider'] = provider

def add_utils(event):
    """
    Add 'utils' dict to the event. This gives our templates access to it.
    """
    workflowsteps = event['request'].registry.getUtility(IWorkflowSteps)
    event['workflowsteps'] = workflowsteps
