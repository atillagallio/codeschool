from django.utils.html import escape
from djinga.register import jj_filter, jj_global
from django.core.urlresolvers import reverse
filter_registry = {}
globals_registry = {}


# "hooks" global variable
class CsHooks:
    """
    Extensible points to be used in templates.
    """

    def __init__(self):
        self.cs_head_links = []

globals_registry['hooks'] = CsHooks()


# "cfg" global variable
class CfgGlobal:
    """
    Expose configurations to templates.
    """

    def __getattr__(self, attr):
        if attr.isupper():
            from codeschool.site.settings import codeschool
            return getattr(codeschool, attr, None)


def url_reverse(url, *args, **kwargs):
    return reverse(url, args=args, kwargs=kwargs)

url_reverse.reverse = reverse
globals_registry['cfg'] = CfgGlobal()
globals_registry['url'] = url_reverse


#
# Filters
#
def register_filter(filter):
    filter_registry[filter.__name__] = filter
    return filter


@register_filter
@jj_filter
def markdown(text, *args, **kwargs):
    """
    Convert a string of markdown source to HTML.
    """

    from markdown import markdown
    return markdown(text, *args, **kwargs)


@register_filter
@jj_filter
def icon(value):
    """
    Convert value to a material-icon icon tag.
    """
    if value is True:
        return '<i class="material-icons">done</i>'
    elif value is False:
        return '<i class="material-icons">error</i>'
    else:
        return '<i class="material-icons">%s</i>' % escape(value)
