from pyramid.view import view_config
from pyramid.renderers import render_to_response

from helpers import BaseHelper
from oerpub.rhaptoslabs.swordpushweb import parse_sword_treatment

class SummaryView(BaseHelper):

    @view_config(route_name='summary')
    def process(self):
        super(SummaryView, self)._process()
        return self.navigate()
    
    def navigate(self, errors=None, form=None):
        # See if this was a plain navigation attempt
        view = super(SummaryView, self)._navigate(errors, form)
        if view:
            return view

        # It was not, let's prepare the default view.
        templatePath = 'templates/summary.pt'
        request = self.request
        deposit_receipt = request.session['deposit_receipt']
        response = parse_sword_treatment.get_requirements(deposit_receipt)
        response['view'] = self
        return render_to_response(templatePath, response, request=request)
