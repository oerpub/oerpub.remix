from zope.interface import implements
from pyramid.view import render_view
from pyramid.exceptions import NotFound

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
    
    DEFAULT_WORKFLOW = ['choose', 'preview', 'metadata', 'summary']

    workflows = {'newemptymodule' : DEFAULT_WORKFLOW,
                 'existingmodule' : DEFAULT_WORKFLOW,
                 'cnxinputs'      : DEFAULT_WORKFLOW,
                 'gdocupload'     : DEFAULT_WORKFLOW,
                 'fileupload'     : DEFAULT_WORKFLOW}
    
    def setWorkflowSteps(self, wf_name, steps):
        wf = self.workflows.get(wf_name)
        if not wf:
            raise NotFound('Workflow %s could not be found.' % wf_name)
        self.workflows[wf_name] = steps
   
    def getWorkflowSteps(self, workflow):
        steps = self.workflows.get(workflow)
        if not steps:
            raise NotFound('Workflow %s could not be found.' % workflow)
        return steps

    def _getCurrentIdx(self, steps, step):
        current_idx = steps.index(step)
        return current_idx
    
    def getNextStep(self, workflow, current_step):
        """
        We use whatever is less the last index in the steps or the current
        step +1. That way we don't try to go beyond the end of the steps.
        """
        steps = self.getWorkflowSteps(workflow)
        current_idx = self._getCurrentIdx(steps, current_step) 
        next_idx = min(current_idx+1, len(steps)+1)
        return steps[next_idx]

    def getPreviousStep(self, workflow, current_step):
        """
        We use whatever is bigger the first index in the steps or the current
        step -1. That way we don't try to go beyond the beginning of the steps.
        """
        steps = self.getWorkflowSteps(workflow)
        current_idx = self._getCurrentIdx(steps, current_step) 
        next_idx = max(current_idx-1, 0)
        return steps[next_idx]
