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

    workflows = {'new_module'               : ['', '', ''],
                 'edit_existing_module'     : [],
                 'import_new_module'        : [],
                 'overwrite_existing_module': []}
   
    def getWorkflowSteps(self, workflow):
        steps = self.workflows.get(workflow)
        if not steps:
            raise NotFound('Workflow %s could not be found.' % workflow)
        return steps

    def _getCurrentIdx(self, workflow, step):
        current_idx = steps.index(current_step)
        if not current_idx:
            raise NotFound('Missing workflow step %d.' % current_step)
        return current_idx
    
    def getNextStep(self, workflow, current_step):
        """
        We use whatever is less the last index in the steps or the current
        step +1. That way we don't try to go beyond the end of the steps.
        """
        steps = self.getWorkflowSteps(workflow)
        current_idx = self._getCurrentIdx(workflow,current_step) 
        next_idx = min(current_idx+1, len(steps)+1)
        return steps[next_idx]

    def getPreviousStep(self, workflow, current_step):
        """
        We use whatever is bigger the first index in the steps or the current
        step -1. That way we don't try to go beyond the beginning of the steps.
        """
        steps = self.getWorkflowSteps(workflow)
        current_idx = self._getCurrentIdx(workflow,current_step) 
        next_idx = max(current_idx-1, 0)
        return steps[next_idx]
