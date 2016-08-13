#
# One stop shop for models, fields and managers
#
from django.db.models.fields.related_descriptors import \
    ReverseManyToOneDescriptor
from lazyutils import lazy

from .fields import *

from django.utils.translation import ugettext_lazy as _
from django.db.models import *
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Group, Permission

from wagtail.wagtailcore.models import Page, Orderable, PageManager, PageQuerySet
from wagtail.contrib.wagtailroutablepage.models import RoutablePage, RoutablePageMixin, route
from wagtail_model_tools.models import SinglePage, SinglePageMixin, SinglePageManager, ProxyPageMixin, CopyMixin, CopyableModel
from wagtail.wagtailadmin.edit_handlers import MultiFieldPanel as _MultiFieldPanel, FieldPanel as _FieldPanel
from modelcluster.models import ClusterableModel

from polymorphic.models import PolymorphicModel, PolymorphicManager
from polymorphic.query import PolymorphicQuerySet

from model_utils.choices import Choices
from model_utils.models import QueryManager, StatusModel, TimeFramedModel, TimeStampedModel
from model_utils.managers import QueryManager, InheritanceManager, QuerySet, InheritanceQuerySet


#
# Patch RoutablePageMixin
#
def _get_subpage_urls(cls):
    routes = []
    for attr in dir(cls):
        val = getattr(cls, attr, None)
        if hasattr(val, '_routablepage_routes'):
            routes.extend(val._routablepage_routes)

    return tuple([
        route[0]
        for route in sorted(routes, key=lambda route: route[1])
    ])

RoutablePageMixin.get_subpage_urls = classmethod(_get_subpage_urls)


#
# Codeschool based managers
#
class RelatedDescriptorExt(ReverseManyToOneDescriptor):
    """
    A descriptor that automatically extends the default related manager
    descriptor by inserting the given ext_class in the mro().
    """
    def __init__(self, descriptor, ext_class):
        super().__init__(descriptor.rel)
        self.descriptor = descriptor
        self.ext_class = ext_class

    @lazy
    def ext_class_final(self):
        # We test these two attributes in order to support ModelCluster
        # descriptors and the vanilla Django ones.
        for attr in ('child_object_manager_cls', 'related_manager_cls'):
            try:
                manager_cls = getattr(self.descriptor, attr)
            except AttributeError:
                continue
            else:
                class DescriptorExt(self.ext_class, manager_cls):
                    def __new__(cls, *args, **kwargs):
                        return manager_cls.__new__(cls, *args, **kwargs)

                    def __init__(self, *args, **kwargs):
                        manager_cls.__init__(self, *args, **kwargs)

                    def __get__(self, instance, cls=None):
                        return manager_cls.__get__(instance, cls=cls)

                    def __getattr__(self, attr):
                        print(manager_cls)
                        if hasattr(manager_cls, '__getattr__'):
                            return super(manager_cls, self).__getattr__(attr)
                        else:
                            raise AttributeError(attr)

                return DescriptorExt

        raise RuntimeError('could not determine the manager class from the'
                           'descriptor: %r' % self.descriptor)

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        return self.ext_class_final(instance)

    def __set__(self, instance, value):
        self.descriptor.__set__(instance, value)


class RelatedManagerExt:
    """
    Base class for implementing extensions for a related manager defined with
    the given `related_name`.
    """

    def __new__(cls, related_name_or_descriptor):
        if isinstance(related_name_or_descriptor, str):
            return cls.__new__(cls, related_name_or_descriptor)

        # We modify the descriptor object to use a new class that inherits from
        # the
        descriptor = related_name_or_descriptor
        return RelatedDescriptorExt(descriptor, cls)

    def __init__(self, related_name):
        self.related_name = related_name
        self._queryset = None
        self._instance = None
        self.model = None

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        return self._bound_copy(self._instance)

    def _bound_copy(self, instance):
        new = object.__new__(type(self))
        new.__dict__.update(self.__dict__)
        new._instance = instance
        new.model = instance.__class__
        new._queryset = getattr(instance, self.related_name)

    def __getattr__(self, attr):
        return getattr(self._queryset, attr)


#
# Codeschool based models
#
class ShortDescriptionPageMixin(Model):
    """
    A mixin for a Page which has a short_description field.
    """

    class Meta:
        abstract = True

    short_description = CharField(
        _('short description'),
        max_length=140,
        help_text=_(
            'A short textual description to be used in titles, lists, etc.'
        )
    )

    def full_clean(self, *args, **kwargs):
        if self.short_description and not self.seo_title:
            self.seo_title = self.short_description
        if not self.short_description:
            self.short_description = self.seo_title or self.title
        return super().full_clean(*args, **kwargs)

    content_panels = Page.content_panels + [
       _MultiFieldPanel([
           _FieldPanel('short_description'),
       ], heading=_('Options')),
    ]


class ShortDescriptionMixin(Model):
    """
    A describable page model that only adds the short_description field,
    leaving the long_description/body definition to the user.
    """

    class Meta:
        abstract = True

    short_description = CharField(
        _('short description'),
        max_length=140,
        blank=True,
        help_text=_(
            'A very brief one-phrase description used in listings.\n'
            'This field accepts mardown markup.'
        ),
    )


class AbsoluteUrlMixin:
    """
    Adds a get_absolute_url() method to a Page object.
    """
    url = None

    def get_absolute_url(self, *urls):
        """
        Return the absolute url of page object.

        Additional arguments append any extra url elements as in the example::

        >>> page.get_absolute_url()
        '/artist/john-lennon'
        >>> pages.get_absolute_urls('songs', 'revolution')
        '/artist/john-lennon/songs/revolution'
        """
        if not urls:
            return self.url
        url = self.url.rstrip('/')
        return '%s/%s/' % (url, '/'.join(urls))

    def get_admin_url(self, list=False):
        """
        Return the Wagtail admin url.
        """

        if list:
            return '/admin/pages/%s/' % self.id
        return '/admin/pages/%s/edit/' % self.id

