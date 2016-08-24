import decimal
import json

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
from lazyutils import lazy_classattribute

from codeschool import blocks
from codeschool import models
from codeschool import panels
from codeschool.lms.gamification.models import HasScorePage
from codeschool.models import AbsoluteUrlMixin

__all__ = []

ZERO = decimal.Decimal(0)
RESOURCE_BLOCKS = [
    ('paragraph', blocks.RichTextBlock()),
    ('image', blocks.ImageChooserBlock()),
    ('embed', blocks.EmbedBlock()),
    # ('markdown', blocks.MarkdownBlock()),
    ('url', blocks.URLBlock()),
    ('text', blocks.TextBlock()),
    ('char', blocks.CharBlock()),
    # ('ace', blocks.AceBlock()),
    ('bool', blocks.BooleanBlock()),
    ('doc', blocks.DocumentChooserBlock()),
    # ('snippet', blocks.SnippetChooserBlock(GradingMethod)),
    ('date', blocks.DateBlock()),
    ('time', blocks.TimeBlock()),
    ('stream', blocks.StreamBlock([
        ('page', blocks.PageChooserBlock()),
        ('html', blocks.RawHTMLBlock())
    ])),
]


class ActivityQueryset(models.PageQuerySet):
    def auth(self, user, role=None):
        """
        Filter only activities that the user can see.
        """

        return self.filter(live=True)


ActivityManager = models.PageManager.from_queryset(ActivityQueryset)


class ActivityMeta(type(models.Page)):
    CONCRETE_ACTIVITY_TYPES = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self._meta.abstract:
            self.CONCRETE_ACTIVITY_TYPES.append(self)


class Activity(AbsoluteUrlMixin, HasScorePage, metaclass=ActivityMeta):
    """
    Represents a gradable activity inside a course. Activities may not have an
    explicit grade, but yet may provide points to the students via the
    gamefication features of Codeschool.

    Activities can be scheduled to be done in the class or as a homework
    assignment.

    Each concrete activity is represented by a different subclass.
    """

    class Meta:
        abstract = True
        verbose_name = _('activity')
        verbose_name_plural = _('activities')

    author_name = models.CharField(
        _('Author\'s name'),
        max_length=100,
        blank=True,
        help_text=_(
            'The author\'s name, if not the same user as the question owner.'
        ),
    )
    objects = ActivityManager()

    #: Define the default material icon used in conjunction with instances of
    #: the activity class.
    personalization_default_icon = 'material:help'

    #: The response class associated with the given activity.
    submission_class = None

    #: Model template
    template = 'lms/activities/activity.jinja2'

    #: Dictionary with extra static content that should be appended to the
    #: context for instances of the model.
    extra_context = {}

    def clean(self):
        super().clean()

        if not self.author_name and self.owner:
            self.author_name = self.owner.get_full_name()

    @property
    def submissions(self):
        return self.submission_class.objects.filter(
            response__activity_page_id=self.id
        )

    # Response control
    # def get_response(self, user=None, context=None):
    #     """
    #     Get the response associated with given user and context.
    #
    #     If no user and context is given, use the bound values.
    #     """
    #
    #     user = self._normalize_user(user)
    #     context = self._normalize_response_context(context)
    #     get_response = apps.get_model('cs_core', 'Response').get_response
    #     return get_response(user=user, context=context, activity=self)

    def submit(self, user, response_data=None, autograde=False,
               recycle=False, submission_kwargs=None):
        """
        Create a new Submission object for the given question and saves it on
        the database.

        Args:
            user:
                The user who submitted the submission.
            response_data:
                A dictionary that is used to initialize the response_data
                attribute of the resulting submission object.
            autograde:
                If true, calls the autograde() method in the submission to
                give the automatic gradings.
            recycle:
                If true, recycle submission objects with the same content as the
                current submission. If a submission exists with the same content
                as the current submission, it simply returns that submission.
                The resulting object have a boolean ``.recycled`` attribute
                that tells if it was recycled or not.
            submission_kwargs:
                A dictionary with extra kwargs to be passed to the class'
                submission_class constructor.
        """

        # Fetch submission class
        try:
            submission_class = self.submission_class
            if submission_class is None:
                raise AttributeError
        except AttributeError:
            raise ImproperlyConfigured(
                '%s must define a submission_class attribute with the '
                'appropriate response class.' % self.__class__.__name__
            )

        # Normalize inputs
        submission_kwargs = submission_kwargs or {}
        response_data = response_data or {}

        # Add response information to the given submission kwargs
        response = self.responses.response_for_user(user)

        # We compute the hash and compare it with values on the database
        # if recycle is enabled
        response_hash = submission_class.response_data_hash(response_data)
        submission = None
        recycled = False
        if recycle:
            recyclable = submission_class.objects.filter(
                response=response,
                response_hash=response_hash,
            ).order_by('created')
            for pk, value in recyclable.values_list('id', 'response_data'):
                if value == response_data:
                    submission = recyclable.get(pk=pk)
                    recycled = True
                    break

        # Proceed if no submission was created
        if submission is None:
            submission = submission_class(
                user=user,
                response=response,
                response_hash=response_hash,
                response_data=response_data,
                **submission_kwargs,
            )

        # Finalize submission item
        submission.autograde()
        submission.recycled = recycled
        return submission

    # def process_response_item(self, response, recycled=False):
    #     """
    #     Process this response item generated by other activities using a context
    #     that you own.
    #
    #     This might happen in compound activities like quizzes, in which the
    #     response to a question uses a context own by a quiz object. This
    #     function allows the container object to take any additional action
    #     after the response is created.
    #     """
    #
    # def has_response(self, user=None, context=None):
    #     """
    #     Return True if the user has responded to the activity.
    #     """
    #
    #     response = self.get_response(user, context)
    #     return response.response_items.count() >= 1
    #
    # def correct_responses(self, context=None):
    #     """
    #     Return a queryset with all correct responses for the given context.
    #     """
    #
    #     done = apps.get_model('cs_core', 'ResponseItem').STATUS_DONE
    #     items = self.response_items(context, status=done)
    #     return items.filter(given_grade=100)
    #
    # def import_responses_from_context(self, from_context, to_context,
    #                                   user=None,
    #                                   discard=False):
    #     """
    #     Import all responses associated with `from_context` to the `to_context`.
    #
    #     If discard=True, responses in the original context are discarded.
    #     """
    #
    #     if from_context == to_context:
    #         raise ValueError('contexts cannot be the same')
    #
    #     responses = self.response_items(user=user, context=from_context)
    #     for response_item in responses:
    #         old_response = response_item.response
    #         new_response = self.get_response(context=to_context,
    #                                          user=old_response.user)
    #         if not discard:
    #             response_item.pk = None
    #         response_item.response = new_response
    #         response_item.save()
    #
    # # Serving pages
    # def response_context_from_request(self, request):
    #     """
    #     Return the context from the request object.
    #     """
    #
    #     try:
    #         context_pk = request.GET['context']
    #         objects = apps.get_model('cs_core', 'ResponseContext').objects
    #         return objects.get(pk=context_pk)
    #     except KeyError:
    #         return self.default_context

    def get_context(self, request, *args, **kwargs):
        return dict(
            super().get_context(request, *args, **kwargs),
            activity=self,
            **self.extra_context,
        )

    # def get_user_response(self, user, method='first'):
    #     """
    #     Return some response given by the user or None if the user has not
    #     responded.
    #
    #     Allowed methods:
    #         unique:
    #             Expects that response is unique and return it (or None).
    #         any:
    #             Return a random user response.
    #         first:
    #             Return the first response given by the user.
    #         last:
    #             Return the last response given by the user.
    #         best:
    #             Return the response with the best final grade.
    #         worst:
    #             Return the response with the worst final grade.
    #         best-given:
    #             Return the response with the best given grade.
    #         worst-given:
    #             Return the response with the worst given grade.
    #
    #     """
    #
    #     responses = self.responses.filter(user=user)
    #     first = lambda x: x.select_subclasses().first()
    #
    #     if method == 'unique':
    #         N = self.responses.count()
    #         if N == 0:
    #             return None
    #         elif N == 1:
    #             return response.select_subclasses().first()
    #         else:
    #             raise ValueError(
    #                 'more than one response found for user %r' % user.username
    #             )
    #     elif method == 'any':
    #         return first(responses)
    #     elif method == 'first':
    #         return first(responses.order_by('created'))
    #     elif method == 'last':
    #         return first(responses.order_by('-created'))
    #     elif method in ['best', 'worst', 'best-given', 'worst-given']:
    #         raise NotImplementedError(
    #             'method = %r is not implemented yet' % method
    #         )
    #     else:
    #         raise ValueError('invalid method: %r' % method)
    #
    # def autograde_all(self, force=False, context=None):
    #     """
    #     Grade all responses that had not been graded yet.
    #
    #     This function may take a while to run, locking the server. Maybe it is
    #     a good idea to run it as a task or in a separate thread.
    #
    #     Args:
    #         force (boolean):
    #             If True, forces the response to be re-graded.
    #     """
    #
    #     # Run autograde on each responses
    #     for response in responses:
    #         response.autograde(force=force)
    #
    # def select_users(self):
    #     """
    #     Return a queryset with all users that responded to the activity.
    #     """
    #
    #     user_ids = self.responses.values_list('user', flat=True).distinct()
    #     users = models.User.objects.filter(id__in=user_ids)
    #     return users
    #
    # def get_grades(self, users=None):
    #     """
    #     Return a dictionary mapping each user to their respective grade in the
    #     activity.
    #
    #     If a list of users is given, include only the users in this list.
    #     """
    #
    #     if users is None:
    #         users = self.select_users()
    #
    #     grades = {}
    #     for user in users:
    #         grade = self.get_user_grade(user)
    #         grades[user] = grade
    #     return grades

    #
    # Plagiarism detection
    #
    def best_responses(self, context):
        """
        Return a dictionary mapping users to their best responses.
        """

        mapping = {}
        responses = self.responses.filter(context=context)
        for response in responses:
            mapping[response.user] = response.best_submission()
        return mapping

    def find_identical_responses(self, context, key=None, cmp=None, thresh=1):
        """
        Finds all responses with identical response_data in the set of best
        responses.

        Args:
            key:
                The result of key(response_data) is used for normalizing the
                different responses in the response set.
            cmp:
                A comparison function that take the outputs of key(x) for a
                pair of responses and return True if the two arguments are to
                be considered equal.
            thresh:
                Minimum threshold for the result of cmp(x, y) to be considered
                plagiarism.
        """

        key = key or (lambda x: x)
        responses = self.best_responses(context).values()
        response_data = [(x, key(x.response_data))
                         for x in responses if x is not None]

        # We iterate this list in O^2 complexity by comparing every pair of
        # responses and checking if cmp(data1, data2) returns a value greater
        # than or equal thresh.
        bad_pairs = {}
        cmp = cmp or (lambda x, y: x == y)
        for i, (resp_a, key_a) in enumerate(response_data):
            for j in range(i + 1, len(response_data)):
                resp_b, key_b = response_data[j]
                value = cmp(key_a, key_b)
                if value >= thresh:
                    bad_pairs[resp_a, resp_b] = value
        return bad_pairs

    def group_identical_responses(self, context, key=None, keep_single=True):
        key = key or (lambda x: json.dumps(x))
        bad_values = {}
        for response in self.best_responses(context).values():
            if response is None:
                continue
            key_data = key(response.response_data)
            response_list = bad_values.setdefault(key_data, [])
            response_list.append(response)

        return bad_values

    #
    # Statistics
    #
    def response_items(self, context=None, status=None, user=None):
        """
        Return a queryset with all response items associated with the given
        activity.

        Can filter by context, status and user
        """

        items = self.response_item_class.objects
        queryset = items.filter(response__activity_id=self.id)

        # Filter context
        if context != 'any':
            context = context or self.context
            queryset = queryset.filter(response__context_id=context.id)

        # Filter user
        user = user or self.user
        if user:
            queryset = queryset.filter(response__user_id=user.id)

        # Filter by status
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def _stats(self, attr, context, by_item=False):
        if by_item:
            items = self.response_items(context, self.STATUS_DONE)
            values_list = items.values_list(attr, flat=True)
            return Statistics(attr, values_list)
        else:
            if context == 'any':
                items = self.responses.all()
            else:
                context = context or self.context
                items = self.responses.all().filter(context=context)
            return Statistics(attr, items.values_list(attr, flat=True))

    def best_final_grade(self, context=None):
        """
        Return the best final grade given for this activity.
        """

        return self._stats('final_grade', context).max()

    def best_given_grade(self, context=None):
        """
        Return the best grade given for this activity before applying any
        penalties and bonuses.
        """

        return self._stats('given_grade', context).min()

    def mean_final_grade(self, context=None, by_item=False):
        """
        Return the average value for the final grade for this activity.

        If by_item is True, compute the average over all response items instead
        of using the responses for each student.
        """

        return self._stats('final_grade', context, by_item).mean()

    def mean_given_grade(self, by_item=False):
        """
        Return the average value for the given grade for this activity.
        """

        return self._stats('given_grade', context, by_item).mean()

    # Permissions
    def can_edit(self, user):
        """
        Return True if user has permissions to edit activity.
        """

        return user == self.owner or self.course.can_edit(user)

    def can_view(self, user):
        """
        Return True if user has permission to view activity.
        """

        course = self.course
        return (
            self.can_edit(user) or
            user in course.students.all() or
            user in self.staff.all()
        )

    # Wagtail admin
    # subpage_types = []
    # parent_page_types = []
    # content_panels = models.Page.content_panels + [
    #    panels.MultiFieldPanel([
    #        # panels.RichTextFieldPanel('short_description'),
    #    ], heading=_('Options')),
    # ]
    # promote_panels = models.Page.promote_panels + [
    #    panels.FieldPanel('icon_src')
    # ]
    settings_panels = models.Page.settings_panels + [
        panels.MultiFieldPanel([
            panels.FieldPanel('points_total'),
            panels.FieldPanel('stars_total'),
        ], heading=_('Scores'))
    ]


class ScoreDescriptor:
    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        return ScoreHandler(obj)


class ScoreHandler:
    """
    Implements the "Activity.score" property.

    This is a manager-like object that handles points and stars associated to an
    activity.
    """

    def __init__(self, instance):
        self.instance = instance

    @lazy_classattribute
    def _user_score(self):
        from codeschool.lms.gamification.models import UserScore
        return UserScore

    @lazy_classattribute
    def _total_score(self):
        from codeschool.lms.gamification.models import TotalScore
        return TotalScore

    def points(self, user):
        """
        Number of points associated to user.
        """

        return self._user_score.load(user, self.instance).points

    def stars(self, user):
        """
        Stars associated to user.
        """

        return self._user_score.load(user, self.instance).stars

    def points_total(self):
        """
        Return the total number of points associated with activity.
        """

        if self.instance.num_child == 0:
            return self.instance.points_total
        return self._total_score.load(self.instance).points

    def stars_total(self):
        """
        Return the total number of stars associated with activity.
        """

        if self.instance.num_child == 0:
            return self.instance.stars_total
        return self._total_score.load(self.instance).stars

Activity.score = ScoreDescriptor()
