from zope.interface import Interface

class IWorkflowSteps(Interface):
    
    def getNextStep(self):
        pass

    def getPreviousStep(self):
        pass
