from pyramid.renderers import get_renderer

def add_base_template(event):
    """
    Expose the base template as per the Pyramid cookbook:

    https://docs.pylonsproject.org/projects/pyramid_cookbook/dev/templates.html#using-a-beforerender-event-to-expose-chameleon-base-template
    """
    base = get_renderer('templates/main_template.pt').implementation()
    event.update({'base': base})
    base = get_renderer('templates/base.pt').implementation()
    event.update({'newbase': base})
    base = get_renderer('templates/base_bare.pt').implementation()
    event.update({'newbasebare': base})
