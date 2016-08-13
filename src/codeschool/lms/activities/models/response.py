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
    given_points = models.IntegerField(default=0)
    given_score = models.IntegerField(default=0)
    given_stars = models.FloatField(default=0.0)

    #: The number of submissions in the current session.
    num_submissions = property(lambda x: x.submissions.count())

    #: Specific activity reference
    activity = property(lambda x: x.activity_page.specific)
    activity_id = property(lambda x: x.activity_page_id)

    @activity.setter
    def activity(self, value):
        self.activity_page = value.page_ptr

    objects = ResponseManager()

    @classmethod
    def get_response(cls, user, activity, context=None):
        """
        Return the response object associated with the given
        user/activity/context.

        Create a new response object if it does not exist.
        """

        if user is None or activity is None:
            raise TypeError(
                'Response objects must be bound to an user or activity.'
            )

        response, create = Response.objects.get_or_create(
            user=user, activity=activity, context=context
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

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Response):
            if self.pk is None:
                return False
            else:
                return self.pk == other.pk
        return NotImplemented

    def update(self, force=False):
        """
        Synchronize object so its state accounts for the latest responses.
        """

        return

        if not self.__updated or self.final_grade is None or force:
            # We check if any response_item was updated after the main response
            # object. If so, we recompute the grades using the maximum grade
            # criterion
            # TODO: in the future we should use grading_method
            changed_items = self.items.filter(modified__gte=self.modified)
            if changed_items or True:
                grades = self.items.values_list('final_grade', flat=True)
                grades = [grade for grade in grades if grade]
                self.final_grade = max(grades, default=self.final_grade or 0)
                self.save(update_fields=['final_grade'])
            elif self.final_grade is None:
                self.final_grade = 0.0
                self.save(update_fields=['final_grade'])
            self.__updated = True

    def update_for_submission(self, submission):
        """
        Called when new submissions are sent or auto-graded.
        """

    def best_submission(self):
        """
        Return the best response item associated with the response.
        """

        if self.items.count():
            best = self.items.order_by('-final_grade')[0]
            if best.final_grade == 0:
                return None
            best_set = self.items.filter(final_grade=best.final_grade)
            return best_set.order_by('created').first()
        return None

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
