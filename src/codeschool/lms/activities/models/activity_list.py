import model_reference
from django.utils.translation import ugettext_lazy as _

from codeschool import models, panels

from .activity import Activity


class ActivityListQuerySet(models.PageQuerySet):
    def create_subpage(self, parent, **kwargs):
        """
        Return a new page as a child of the given parent page.
        """

        return self.model.create_subpage(parent, **kwargs)


class _ActivityListManager(models.PageManager):
    def main(self):
        """
        Return the main ActivityList for the website.
        """

        return model_reference.load('root-page', model=ActivityList)

ActivityListManager = _ActivityListManager.from_queryset(ActivityListQuerySet)


class ActivityList(models.ShortDescriptionPageMixin, models.Page):
    """
    A list of ActivitySections.
    """

    class Meta:
        verbose_name = _('list of activities')
        verbose_name_plural = _('lists of activities')

    BEGINNER_SECTIONS = [
        'basic', 'conditionals', 'loops', 'functions', 'files', 'lists'
    ]
    INTERMEDIATE_SECTIONS = [
        'classes', 'iterators',  # whatnot...
    ]
    MARATHON_SECTIONS = [
        'graphs', 'lists', 'strings',
    ]

    # Templates
    @classmethod
    def create_subpage(cls, parent=None, **kwargs):
        """
        Create a new ActivityList using the given keyword arguments under the
        given parent page. If no parent is chosen, uses the main Wagtail root
        page.
        """

        kwargs.update(
            title=_('Activities'),
            short_description=_('Activities'),
            slug='activities',
        )
        parent = parent or model_reference.load('root-page')
        new = cls(**kwargs)
        parent.add_child(instance=new)
        new.save()
        return new

    @classmethod
    def from_template(cls, template, parent=None):
        """
        Creates a new instance from the given template.

        Valid templates are:
            beginner
                Basic sections in a beginner programming course.
            intermediate
                Sections for a second course on programming course.
            marathon
                Sections for a marathon based course.
        """

        try:
            factory = getattr(cls, '_template_%s' % template)
            return factory(parent)
        except AttributeError:
            raise ValueError('invalid template name: %r' % template)

    @classmethod
    def _template_beginner(cls, parent):
        new = cls.create_subpage(parent)
        for section in cls.BEGINNER_SECTIONS:
            ActivitySection.from_template(section, new)
        return new

    @classmethod
    def _template_intermediate(cls, parent):
        new = cls.create_subpage(parent)
        for section in cls.INTERMEDIATE_SECTIONS:
            ActivitySection.from_template(section, new)
        return new

    @classmethod
    def _template_marathon(cls, parent):
        new = cls.create_subpage(parent)
        for section in cls.MARATHON_SECTIONS:
            ActivitySection.from_template(section, new)
        return new

    # Serving pages
    template = 'lms/activities/list.jinja2'

    def get_context(self, request, *args, **kwargs):
        return dict(
            super().get_context(request, *args, **kwargs),
            object_list=[obj.specific for obj in self.get_children()]
        )

    # Wagtail admin
    subpage_types = ['ActivitySection']


class ActivitySection(models.ShortDescriptionPageMixin, models.Page):
    """
    List of activities.
    """

    class Meta:
        verbose_name = _('section')
        verbose_name_plural = _('sections')

    material_icon = models.CharField(
        _('Optional icon'),
        max_length=20,
        default='help',
    )
    objects = ActivityListManager()

    @property
    def activities(self):
        return [x.specific for x in self.get_children()]

    def save(self, *args, **kwargs):
        if self.title is None:
            self.title = _('List of activities')
        if self.slug is None:
            self.slug = 'activities'
        super().save(*args, **kwargs)

    # Special template constructors
    @classmethod
    def create_subpage(cls, parent=None, **kwargs):
        """
        Create a new ActivitySection using the given keyword arguments under the
        given parent page. If no parent is chosen, uses the "main-activity-list"
        reference.
        """
        parent = parent or model_reference.load('main-activity-list')
        new = cls(**kwargs)
        parent.add_child(instance=new)
        new.save()
        return new

    @classmethod
    def from_template(cls, template, parent=None):
        """
        Creates a new instance from the given template.

        Valid templates are:
            basic
                Very basic beginner IO based problems. First contact with
                programming.
            conditionals
                Simple problems based on if/else flow control.
            loops
                Problems that uses for/while loops.
            functions
                Problems that uses functions.
            files
                Reading and writing files.
            lists
                Linear data structures such as lists and arrays.
        """

        try:
            factory = getattr(cls, '_template_%s' % template)
            return factory(parent)
        except AttributeError:
            raise ValueError('invalid template name: %r' % template)

    @classmethod
    def _template_basic(cls, parent):
        return cls.create_subpage(
            parent,
            title=_('Basic'),
            short_description=_('Elementary programming problems.'),
            slug='basic',
            material_icon='insert_emoticon',
        )

    @classmethod
    def _template_conditionals(cls, parent):
        return cls.create_subpage(
            parent,
            title=_('Conditionals'),
            short_description=_('Conditional flow control (if/else).'),
            slug='conditionals',
            material_icon='code',
        )

    @classmethod
    def _template_loops(cls, parent):
        return cls.create_subpage(
            parent,
            title=_('Loops'),
            short_description=_('Iterations with for/while commands.'),
            slug='loops',
            material_icon='loop',
        )

    @classmethod
    def _template_functions(cls, parent):
        return cls.create_subpage(
            parent,
            title=_('Functions'),
            short_description=_('Organize code using functions.'),
            slug='functions',
            material_icon='functions',
        )

    @classmethod
    def _template_files(cls, parent):
        return cls.create_subpage(
            parent,
            title=_('Files'),
            short_description=_('Open, process and write files.'),
            slug='files',
            material_icon='insert_drive_file',
        )

    @classmethod
    def _template_lists(cls, parent):
        return cls.create_subpage(
            parent,
            title=_('Lists'),
            short_description=_('Linear data structures.'),
            slug='lists',
            material_icon='list',
        )

    # Serving pages
    template = 'lms/activities/section.jinja2'

    def get_context(self, request, *args, **kwargs):
        return dict(
            super().get_context(request, *args, **kwargs),
            object_list=[obj.specific for obj in self.get_children()]
        )

    # Wagtail Admin
    parent_types = [ActivityList]
    subpage_types = Activity.CONCRETE_ACTIVITY_TYPES
    content_panels = models.ShortDescriptionPageMixin.content_panels + [
        panels.FieldPanel('material_icon')
    ]


@model_reference.factory('main-activity-list')
def make_main_activity_dashboard():
    """
    Creates the default site-wide activity list. Other activity lists may
    appear under different sections in the site.
    """

    parent_page = model_reference.load('root-page')
    activity_list = ActivityList(
        title='Activities',
        slug='activities',
    )
    return parent_page.add_child(instance=activity_list)
