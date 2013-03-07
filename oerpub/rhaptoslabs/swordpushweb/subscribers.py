from pyramid.renderers import get_renderer
from .provider import Provider
from .interfaces import IWorkflowSteps

def add_base_template(event):
    """
    Expose the several macro templates as per the Pyramid cookbook:

    https://docs.pylonsproject.org/projects/pyramid_cookbook/dev/templates.html#using-a-beforerender-event-to-expose-chameleon-base-template
    """
    base = get_renderer('views/templates/base.pt').implementation()
    event.update({'base': base})

    dialogs = get_renderer('views/templates/dialogs.pt').implementation()
    event.update({'dialogs': dialogs})

    macros = get_renderer('views/templates/macros.pt').implementation()
    event.update({'macros': macros})

def add_provider(event):
    """
    Add a provider() callable whereby views can be used inside other
    views/templates, much like zope/plone providers. """
    provider = Provider(event['context'], event['request'])
    event['provider'] = provider

def add_utils(event):
    """
    We do a lookup against the application registry and add the result to the
    event dictionary. That makes 'workflowsteps' accessible in the the
    templates.
    """
    workflowsteps = event['request'].registry.getUtility(IWorkflowSteps)
    event['workflowsteps'] = workflowsteps
