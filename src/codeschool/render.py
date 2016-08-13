from functools import singledispatch
from django.template.loader import render_to_string as _render_to_string

render_registry = {}


@singledispatch
def render_html(object, template_name=None, context=None,
                object_context_name=None):
    """Renders object with the template with the given template name.

    A context with additional variables can be given. By default, it renders
    the template with a context that contains the passed `object`, which is
    saved both in a context variable named object "object" and in variable named
    with the value of `object_context_name`.

    If not given, `object_context_name`  assumes the value of the object's type
    in lowercase.

    This function accepts single argument dispatch and can be overridden to
    specific types using::

        @render_html.register(FooType)
        def _(object, template_name=None, context=None, **kwargs):
            template_name = 'render/foo_template.jinja2'

            # compute something that is pertinent to foo objects
            context = {...}

            # You can call render_html_base to proceed with the usual rendering
            context['foo_instance'] = object
            return render_html(object, template_name, context, **kwargs)

    It is not necessary to override the render function just set a default
    template_name value. Just use the register_template function::

        register_template(FooModel, 'render/foomodel_template.jinja2')
    """

    context = dict(context or ())
    context['object'] = object
    return render_html_base(object, template_name, context, object_context_name)


def render_html_base(object, template_name=None, context=None,
                     object_context_name=None):
    """
    Super-like end point for generic render implementations.
    """

    # Prepare context
    context = dict(context or ())
    context.setdefault(object_context_name or 'object', object)
    if object_context_name is None:
        object_context_name = type(object).__name__.lower()
        context.setdefault(object_context_name, object)

    # Choose template and render
    if template_name is None:
        template_name = render_registry.get(
            type(object), [
                'render/%s.jinja2' % object_context_name,
                'render/default.jinja2'
            ])

    return _render_to_string(template_name, context=context)


def register_template(cls, template_name):
    """
    Register the default template name for the given type.
    """

    if render_registry.get(cls, template_name) != template_name:
        raise ValueError('cannot register %s type twice.' % cls.__name__)
    render_registry[cls] = template_name


render_html.register_template = register_template
