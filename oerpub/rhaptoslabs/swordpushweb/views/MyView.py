from decorators import main_template

@main_template
def MyView(request):
    return { 'project':'SwordPush' }

