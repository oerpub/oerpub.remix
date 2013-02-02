from zope.interface import implements
from pyramid.view import render_view

from .interfaces import IWorkflowSteps

class Provider(object):
    """ Simple provider callable that allows us to traverse to views in our
        templates, hooked into the template context using the BeforeRender
        event. Allows us to insert one view into another using
        provider('viewname'). """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, name='', secure=True):
        context = self.context
        return render_view(context, self.request, name, secure)

class WorkflowStepsUtility(object):
    implements(IWorkflowSteps)
