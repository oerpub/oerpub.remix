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
    
    # Take new content, allow some editing and then create a new module in cnx
    # from this new content.
    DEFAULT = ['choose',
               'preview',
               'metadata',
               'summary']
    
    # Totally new module content that will replace the chosen module in cnx.
    REPLACE_EXISTING_WITH_NEW = ['choose',
                                 'preview',
                                 'module_association',
                                 'metadata',
                                 'summary']
    
    # Select a module form cnx, download, edit it and then replace the old one
    # in cnx with the newly edited content.
    REPLACE_EXISTING_WITH_EDITED = ['choose',
                                    'choose-module',
                                    'preview',
                                    'metadata',
                                    'summary']
    
    # These workflow names are in the format [source]:[target]
    # The 'source' and 'target' values are currently kept on the session.
    workflows = {'new:new'                       : DEFAULT,
                 'newemptymodule:new'            : DEFAULT,
                 'new:existingmodule'            : REPLACE_EXISTING_WITH_NEW,
                 'existingmodule:existingmodule' : REPLACE_EXISTING_WITH_EDITED,
                 'fileupload:new'                : DEFAULT,
                 'fileupload:existingmodule'     : REPLACE_EXISTING_WITH_NEW,
                 'gdocupload:new'                : DEFAULT,
                 'gdocupload:existingmodule'     : REPLACE_EXISTING_WITH_NEW,
                 'url:new'                       : DEFAULT,
                 'url:existingmodule'            : REPLACE_EXISTING_WITH_NEW,
                 'cnxinputs:new'                 : DEFAULT,
                 'cnxinputs:existingmodule'      : REPLACE_EXISTING_WITH_NEW,
                 'presentation:new'              : DEFAULT,
                 'presentation:existingmodule'   : REPLACE_EXISTING_WITH_NEW,
                }
    
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
