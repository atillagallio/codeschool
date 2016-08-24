from django.utils.translation import ugettext_lazy as _

from codeschool import models


class ResponseQuerySet(models.PolymorphicQuerySet):
    """
    QuerySet for Session objects.
    """


class ResponseManager(models.PolymorphicManager):
    """
    Manager for Session objects.
    """

    use_for_related_fields = True
    queryset_class = ResponseQuerySet

    def response_for_request(self, request, activity=None):
        """
        Return session associated with the request object.
        """

        return self.response_for_user(request.user, activity)

    def response_for_user(self, user, activity=None):
        """
        Return session associated with the given user.
        """

        session, _ = self.get_or_create(user=user, activity_page=activity)
        return session


class Response(models.CopyMixin,
               models.StatusModel,
               models.TimeStampedModel,
               models.PolymorphicModel,
               models.ClusterableModel):
    """
    When an user starts an activity it opens a Session object that controls
    how responses to the given activity will be submitted.

    The session object manages individual response submissions that may span
    several http requests.
    """

    class Meta:
        unique_together = [('user', 'activity_page')]
        verbose_name = _('final response')
        verbose_name_plural = _('final responses')

    STATUS_OPENED = 'opened'
    STATUS_CLOSED = 'closed'
    STATUS_INCOMPLETE = 'incomplete'
    STATUS_WAITING = 'waiting'
    STATUS_INVALID = 'invalid'
    STATUS_DONE = 'done'

    STATUS = models.Choices(
        (STATUS_OPENED, _('opened')),
        (STATUS_CLOSED, _('closed')),
    )

    user = models.ForeignKey(
        models.User,
        related_name='responses',
        on_delete=models.CASCADE,
    )
    activity_page = models.ForeignKey(
        models.Page,
        related_name='responses',
        on_delete=models.CASCADE,
    )
    grade = models.DecimalField(
        _('given grade'),
        max_digits=6,
        decimal_places=3,
        blank=True,
        null=True,
        default=0,
        help_text=_(
            'Grade given to response considering all submissions, penalties, '
            'etc.'
        ),
    )
    finish_time = models.DateTimeField(
        blank=True,
        null=True,
    )
    points = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    stars = models.FloatField(default=0.0)
    is_finished = models.BooleanField(default=bool)
    is_correct = models.BooleanField(default=bool)
    objects = ResponseManager()

    #: The number of submissions in the current session.
    num_submissions = property(lambda x: x.submissions.count())

    #: Specific activity reference
    activity = property(lambda x: x.activity_page.specific)
    activity_id = property(lambda x: x.activity_page_id)

    @activity.setter
    def activity(self, value):
        self.activity_page = value.page_ptr

    @classmethod
    def _get_response(cls, user, activity):
        """
        Return the response object associated with the given
        user/activity.

        Create a new response object if it does not exist.
        """

        if user is None or activity is None:
            raise TypeError(
                'Response objects must be bound to an user or activity.'
            )

        response, create = Response.objects.get_or_create(
            user=user, activity=activity
        )
        return response

    def __repr__(self):
        tries = self.num_submissions
        user = self.user
        activity = self.activity
        class_name = self.__class__.__name__
        grade = '%s pts' % (self.grade or 0)
        fmt = '<%s: %s by %s (%s, %s tries)>'
        return fmt % (class_name, activity, user, grade, tries)

    def __str__(self):
        return repr(self)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Response):
            if self.pk is None:
                return False
            else:
                return self.pk == other.pk
        return NotImplemented

    def register_submission(self, submission):
        """
        This method is called when a submission is graded.
        """

        assert submission.response_id == self.id

        # Register points and stars associated with submission.
        score_kwargs = {}
        final_points = submission.final_points()
        final_stars = submission.final_stars()
        if final_points > self.points:
            score_kwargs['points'] = final_points - self.points
            self.points = final_points
        if final_stars > self.stars:
            score_kwargs['stars'] = final_stars - self.stars
            self.stars = final_stars

        # If some score has changed, we save the update fields and update the
        # corresponding UserScore object
        if score_kwargs:
            from codeschool.lms.gamification.models import UserScore
            self.save(update_fields=score_kwargs.keys())
            score_kwargs['diff'] = True
            UserScore.update(self.user, self.activity_page, **score_kwargs)

    def regrade(self, method=None, force_update=False):
        """
        Return the final grade for the user using the given method.

        If not method is given, it uses the default grading method for the
        activity.
        """

        activity = self.activity

        # Choose grading method
        if method is None and self.final_grade is not None:
            return self.final_grade
        elif method is None:
            grading_method = activity.grading_method
        else:
            grading_method = GradingMethod.from_name(activity.owner, method)

        # Grade response. We save the result to the final_grade attribute if
        # no explicit grading method is given.
        grade = grading_method.grade(self)
        if method is None and (force_update or self.final_grade is None):
            self.final_grade = grade
        return grade
