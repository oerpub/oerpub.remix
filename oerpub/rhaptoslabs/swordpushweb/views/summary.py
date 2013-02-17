from pyramid.view import view_config
from pyramid.renderers import render_to_response

from helpers import BaseHelper
from oerpub.rhaptoslabs.swordpushweb import parse_sword_treatment

class SummaryView(BaseHelper):

    @view_config(route_name='summary')
    def generate_html_view(self):
        self.check_login()
        templatePath = 'templates/summary.pt'
        
        request = self.request
        deposit_receipt = request.session['deposit_receipt']
        response = parse_sword_treatment.get_requirements(deposit_receipt)
        response['view'] = self
        return render_to_response(
            templatePath, response, request=request)


