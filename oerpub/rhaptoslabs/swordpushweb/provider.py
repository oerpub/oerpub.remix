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
    EXISTING_MODULE_WORKFLOW = ['choose', 'choose-module', 'preview', 'metadata', 'summary']
    EXISTING_MODULE_NEW_WORKFLOW = ['choose', 'choose-module', 'preview', 'metadata', 'summary']

    workflows = {'new:new'                       : DEFAULT_WORKFLOW,
                 'existingmodule:existingmodule' : EXISTING_MODULE_WORKFLOW,
                 'existingmodule:new'            : EXISTING_MODULE_NEW_WORKFLOW,
                 'newemptymodule' : DEFAULT_WORKFLOW,
                 'cnxinputs'      : DEFAULT_WORKFLOW,
                 'gdocupload'     : DEFAULT_WORKFLOW,
                 'presentation'   : DEFAULT_WORKFLOW,
                 'fileupload'     : DEFAULT_WORKFLOW}
    
    def setWorkflowSteps(self, wf_name, steps):
        wf = self.workflows.get(wf_name)
        if not wf:
            raise NotFound('Workflow %s could not be found.' % wf_name)
        self.workflows[wf_name] = steps
   
    def getWorkflowSteps(self, wf_name):
        steps = self.workflows.get(wf_name)
        if not steps:
            raise NotFound('Workflow %s could not be found.' % wf_name)
        return steps

    def _getCurrentIdx(self, steps, step):
        current_idx = steps.index(step)
        return current_idx
    
    def getNextStep(self, source, target, current_step):
        """
        We use whatever is less the last index in the steps or the current
        step +1. That way we don't try to go beyond the end of the steps.
        """
        wf_name = self.getWorkflowName(source, target)
        steps = self.getWorkflowSteps(wf_name)
        current_idx = self._getCurrentIdx(steps, current_step) 
        next_idx = min(current_idx+1, len(steps)+1)
        return steps[next_idx]

    def getPreviousStep(self, source, target, current_step):
        """
        We use whatever is bigger the first index in the steps or the current
        step -1. That way we don't try to go beyond the beginning of the steps.
        """
        wf_name = self.getWorkflowName(source, target)
        steps = self.getWorkflowSteps(wf_name)
        current_idx = self._getCurrentIdx(steps, current_step) 
        next_idx = max(current_idx-1, 0)
        return steps[next_idx]
    
    def getWorkflowName(self, source, target):
        return '%s:%s' % (source, target)
