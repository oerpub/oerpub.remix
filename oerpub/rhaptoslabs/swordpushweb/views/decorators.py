from pyramid.renderers import get_renderer

def main_template(f):
    """
    A decorator function to provide the main template to views.
    """
    def wrapper(request, *args, **kwargs):
        original_dict = f(request, *args, **kwargs)
        main = get_renderer('../templates/main_template.pt').implementation()
        if 'main' not in original_dict:
            original_dict['main'] = main
        return original_dict
    wrapper.__name__ = f.__name__
    wrapper.__doc__ = f.__doc__
    wrapper.__dict__.update(f.__dict__)
    return wrapper

