import logging
import os

import srvice
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from wagtail.wagtailadmin.forms import WagtailAdminPageForm

from codeschool import blocks
from codeschool import models
from codeschool import panels
from codeschool.lms.activities.models import Activity, Submission
from codeschool.render import render_html

logger = logging.getLogger('codeschool.questions')
QUESTION_BODY_BLOCKS = [
    ('paragraph', blocks.RichTextBlock()),
    ('heading', blocks.CharBlock(classname='full title')),
    ('markdown', blocks.MarkdownBlock()),
    ('html', blocks.RawHTMLBlock()),
]


class QuestionAdminModelForm(WagtailAdminPageForm):
    """
    Create title and short_description fields to make it pass basic validation
    if a import_file is defined.
    """

    def __init__(self, data=None, files=None, instance=None, **kwargs):
        if files and 'import_file' in files:
            file = files['import_file']
            post_data = instance.load_from_file_data(file)
            data = data.copy()
            for field, value in post_data.items():
                if not data[field]:
                    data[field] = value
        super().__init__(data, files, instance=instance, **kwargs)


class QuestionMeta(type(Activity)):
    CONCRETE_QUESTION_TYPES = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self._meta.abstract:
            self.CONCRETE_QUESTION_TYPES.append(self)


class Question(models.RoutablePageMixin,
               models.ShortDescriptionPageMixin,
               Activity, metaclass=QuestionMeta):
    """
    Base abstract class for all question types.
    """

    class Meta:
        abstract = True
        permissions = (("download_question", "Can download question files"),)

    EXT_TO_METHOD_CONVERSIONS = {'yml': 'yaml'}
    OPTIONAL_IMPORT_FIELDS = ['author_name', 'comments', 'score_value',
                              'star_value']
    base_form_class = QuestionAdminModelForm

    body = models.StreamField(
        QUESTION_BODY_BLOCKS,
        blank=True,
        null=True,
        verbose_name=_('Question description'),
        help_text=_(
            'Describe what the question is asking and how should the students '
            'answer it as clearly as possible. Good questions should not be '
            'ambiguous.'
        ),
    )
    comments = models.RichTextField(
        _('Comments'),
        blank=True,
        help_text=_('(Optional) Any private information that you want to '
                    'associate to the question page.')
    )
    import_file = models.FileField(
        _('import question'),
        null=True,
        blank=True,
        upload_to='question-imports',
        help_text=_(
            'Fill missing fields from question file. You can safely leave this '
            'blank and manually insert all question fields.'
        )
    )
    __imported_data = None

    def load_from_file_data(self, file_data):
        """
        Import content from raw file data.
        """

        fmt = self.loader_format_from_filename(file_data.name)
        self.load_from(file_data, format=fmt)
        self.__imported_data = dict(self.__dict__)

        logger.info('Imported question "%s" from file "%s"' %
                    (self.title, self.import_file.name))

        # We fake POST data after loading data from file in order to make the
        # required fields to validate. This part constructs a dictionary that
        # will be used to feed a fake POST data in the QuestionAdminModelForm
        # instance
        fake_post_data = {
            'title': self.title or _('Untitled'),
            'short_description': self.short_description or _('untitled'),
        }

        for field in self.OPTIONAL_IMPORT_FIELDS:
            if getattr(self, field, None):
                fake_post_data[field] = getattr(self, field)

        base_slug = slugify(fake_post_data['title'])
        auto_generated_slug = self._get_autogenerated_slug(base_slug)
        fake_post_data['slug'] = auto_generated_slug
        return fake_post_data

    def loader_format_from_filename(self, name):
        """
        Returns a string with the loader method from the file extension
        """

        _, ext = os.path.splitext(name)
        ext = ext.lstrip('.')
        return self.EXT_TO_METHOD_CONVERSIONS.get(ext, ext)

    def load_from(self, data, format='yaml'):
        """
        Load data from the given file or string object using the specified
        method.
        """

        try:
            loader = getattr(self, 'load_from_%s' % format)
        except AttributeError:
            raise ValueError('format %r is not implemented' % format)
        return loader(data)

    def full_clean(self, *args, **kwargs):
        if self.__imported_data is not None:
            blacklist = {
                # References
                'id', 'owner_id', 'page_ptr_id', 'content_type_id',

                # Saved fields
                'title', 'short_description', 'seo_title', 'author_name',
                'slug', 'comments', 'score_value', 'stars_value', 'difficulty',

                # Forbidden fields
                'import_file',

                # Wagtail fields
                'path', 'depth', 'url_path', 'numchild', 'go_live_at',
                'expire_at', 'show_in_menus', 'has_unpublished_changes',
                'latest_revision_created_at', 'first_published_at',
                'live', 'expired', 'locked',
                'search_description',
            }

            data = {k: v
                    for k, v in self.__imported_data.items()
                    if (not k.startswith('_')) and k not in blacklist and
                    v not in (None, '')}

            for k, v in data.items():
                setattr(self, k, v)

        super().full_clean(*args, **kwargs)

    # Serve pages
    def get_context(self, request, *args, **kwargs):
        return dict(
            super().get_context(request, *args, **kwargs),
            response=self.responses.response_for_request(request),
            question=self,
            form_name='response-form',
        )

    @srvice.route(r'^submit-response/$')
    def route_submit(self, client, **kwargs):
        """
        Handles student responses via AJAX and a srvice program.
        """

        response = self.submit(user=client.user, **kwargs)
        response.autograde()
        data = render_html(response)
        client.dialog(html=data)

    @models.route(r'^submissions/$')
    def route_submissions(self, request, *args, **kwargs):
        submissions = self.submissions.user(request.user).order_by('-created')
        context = self.get_context(request, *args, **kwargs)
        context['submissions'] = submissions

        # Fetch template name from explicit configuration or compute the default
        # value from the class name
        try:
            template = getattr(self, 'template_submissions')
            return render(request, template, context)
        except AttributeError:
            name = self.__class__.__name__.lower()
            if name.endswith('question'):
                name = name[:-8]
            template = 'questions/%s/submissions.jinja2' % name

            try:
                return render(request, template, context)
            except TemplateDoesNotExist:
                raise ImproperlyConfigured(
                    'Model %s must define a template_submissions attribute. '
                    'You  may want to extend this template from '
                    '"questions/submissions.jinja2"' % self.__class__.__name__
                )

    @models.route(r'^leaderboard/$')
    @models.route(r'^statistics/$')
    @models.route(r'^submissions/$')
    @models.route(r'^social/$')
    def route_page_does_not_exist(self, request):
        return render(request, 'base.jinja2', {
            'content_body': 'The page you are trying to see is not implemented '
                            'yet.',
            'content_title': 'Not implemented',
            'title': 'Not Implemented'
        })

    # Wagtail admin
    subpage_types = []
    content_panels = models.ShortDescriptionPageMixin.content_panels[:-1] + [
        panels.MultiFieldPanel([
            panels.FieldPanel('import_file'),
            panels.FieldPanel('short_description'),
        ], heading=_('Options')),
        panels.StreamFieldPanel('body'),
        panels.MultiFieldPanel([
            panels.FieldPanel('author_name'),
            panels.FieldPanel('comments'),
        ], heading=_('Optional information'),
            classname='collapsible collapsed'),
    ]


class QuestionSubmission(Submission):
    """
    Proxy class for responses to questions.
    """

    class Meta:
        proxy = True

    question = property(lambda x: x.response.activity.specific)
    question_id = property(lambda x: x.response.activity_id)

    def __init__(self, *args, **kwargs):
        # Make question an alias to activity.
        question = kwargs.pop('question', None)
        if question is not None:
            kwargs.setdefault('activity', question)
        super().__init__(*args, **kwargs)

# #
# # Gradebook object (move somewhere else)
# #
# class UserGradebook:
#     def __init__(self, questions, user):
#         self.questions = questions
#         self.user = user
#
#     def __iter__(self):
#         user = self.user
#         for question in self.questions:
#             response = question.get_response(user)
#             attempts = response.num_attempts
#             response.update(force=True)
#             grade = response.final_grade
#             url = question.get_absolute_url()
#             title = escape(question.title)
#             question_link = '<a href="%s">%s</a>' % (url, title)
#             yield (question_link, attempts, '%.1f%%' % grade)
#
#     def render(self):
#         head = _('Question'), _('# attempts'), _('Final grade')
#         lines = [
#             '<table class="gradebook">',
#             '<thead>',
#             '<tr><th>%s</th><th>%s</th><th>%s</th></tr>' % head,
#             '</thead>',
#             '<tbody>',
#         ]
#         for (question, N, grade) in self:
#             line = question, N, grade
#             line = ''.join('<td>%s</td>' % elem for elem in line)
#             line = '<tr>%s</tr>' % line
#             lines.append(line)
#         lines.extend([
#             '</tbody>',
#             '</table>'
#         ])
#         return '\n'.join(lines)
#
#     def __html__(self):
#         return self.render()
#
#     def __str__(self):
#         return self.render()
#
#
# class ClassGradebook:
#     def __init__(self, questions=None, users=None):
#         self.questions = list(questions or self._all_questions())
#         self.users = list(users or self._all_users())
#         self.columns = [q.slug for q in self.questions]
#         self.rows = [self._row(user) for user in self.users]
#
#     def _row(self, user):
#         row = []
#         for question in self.questions:
#             response = question.get_response(
#                 user=user,
#                 context=question.default_context
#             )
#             row.append(response.final_grade)
#         return row
#
#     def _all_users(self):
#         return models.User.objects.exclude(username='AnonymousUser')
#
#     def _all_questions(self):
#         ctypes = question_content_types()
#         return models.Page.objects.filter(content_type__in=ctypes).specific()
#
#     def render(self):
#         head = [_('Student')] + self.columns
#         head = ''.join('<th>%s</th>' % x for x in head)
#         lines = [
#             '<table class="gradebook">',
#             '<thead>',
#             '<tr>%s</tr>' % head,
#             '</thead>',
#             '<tbody>',
#         ]
#         for (user, row) in zip(self.users, self.rows):
#             line = [user.get_full_name() or user.username]
#             line.extend(row)
#             line = ''.join('<td>%s</td>' % x for x in line)
#             line = '<tr>%s</tr>' % line
#             lines.append(line)
#         lines.extend([
#             '</tbody>',
#             '</table>'
#         ])
#         return '\n'.join(lines)
#
#     def render_csv(self):
#         data = [',' + ','.join(self.columns)]
#         for user, row in zip(self.users, self.rows):
#             line = [user.username]
#             line.extend(row)
#             data.append(','.join(map(str, line)))
#         return '\n'.join(data)
#
#     def __str__(self):
#         return self.render()
#
#     def __html__(self):
#         return self.render()
#
#
# def question_content_types():
#     ct_getter = models.ContentType.objects.get
#     return (
#         ct_getter(app_label='cs_questions', model='formquestion'),
#         ct_getter(app_label='cs_questions', model='codingioquestion')
#     )