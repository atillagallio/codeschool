import decimal
import hashlib
import json
from decimal import Decimal
from functools import singledispatch

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
from lazyutils import delegate_to
from markdown import markdown

from codeschool import models
from codeschool.lms.activities.models import Response
from codeschool.lms.activities.signals import autograde_signal
from .mixins import ResponseDataMixin, FeedbackDataMixin


class GradingError(Exception):
    """
    Error raised during grading operations.
    """


class SubmissionQuerySet(models.PolymorphicQuerySet):
    def user(self, user):
        """
        Filter submissions by user.
        """

        return self.filter(response__user=user)


class _SubmissionManager(models.PolymorphicManager):
    use_for_related_fields = True


SubmissionManager = _SubmissionManager.from_queryset(SubmissionQuerySet)


class Submission(ResponseDataMixin,
                 FeedbackDataMixin,
                 models.CopyMixin,
                 models.StatusModel,
                 models.TimeStampedModel,
                 models.PolymorphicModel):
    """
    Represents a student's simple submission in response to some activity.

    Submissions can be in 4 different states:

    pending:
        The response has been sent, but was not graded. Grading can be manual or
        automatic, depending on the activity.
    waiting:
        Waiting for manual feedback.
    incomplete:
        For long-term activities, this tells that the student started a response
        and is completing it gradually, but the final response was not achieved
        yet.
    invalid:
        The response has been sent, but contains malformed data.
    done:
        The response was graded and evaluated and it initialized a feedback
        object.

    A response always starts at pending status. We can request it to be graded
    by calling the :func:`Response.autograde` method. This method must raise
    an InvalidResponseError if the response is invalid or ManualGradingError if
    the response subclass does not implement automatic grading.
    """

    class Meta:
        verbose_name = _('submission')
        verbose_name_plural = _('submissions')

    # Feedback messages
    MESSAGE_OK = _(
        '*Congratulations!* Your response is correct!'
    )
    MESSAGE_OK_WITH_PENALTIES = _(
        'Your response is correct, but you did not achieved the maximum grade.'
    )
    MESSAGE_WRONG = _(
        'I\'m sorry, your response is wrong.'
    )
    MESSAGE_PARTIAL = _(
        'Your answer is partially correct: you achieved only %(grade)d%% of '
        'the total grade.'
    )
    MESSAGE_NOT_GRADED = _(
        'Your response has not been graded yet!'
    )

    # Status
    STATUS_PENDING = 'pending'
    STATUS_INCOMPLETE = 'incomplete'
    STATUS_WAITING = 'waiting'
    STATUS_INVALID = 'invalid'
    STATUS_DONE = 'done'

    # Fields
    STATUS = models.Choices(
        (STATUS_PENDING, _('pending')),
        (STATUS_INCOMPLETE, _('incomplete')),
        (STATUS_WAITING, _('waiting')),
        (STATUS_INVALID, _('invalid')),
        (STATUS_DONE, _('done')),
    )

    response = models.ParentalKey(
        'Response',
        related_name='submissions',
    )
    given_grade = models.DecimalField(
        _('percentage of maximum grade'),
        help_text=_(
            'This grade is given by the auto-grader and represents the grade '
            'for the response before accounting for any bonuses or penalties.'
        ),
        max_digits=6,
        decimal_places=3,
        blank=True,
        null=True,
    )
    final_grade = models.DecimalField(
        _('final grade'),
        help_text=_(
            'Similar to given_grade, but can account for additional factors '
            'such as delay penalties or for any other reason the teacher may '
            'want to override the student\'s grade.'
        ),
        max_digits=6,
        decimal_places=3,
        blank=True,
        null=True,
    )
    manual_override = models.BooleanField(
        default=False
    )
    objects = SubmissionManager()

    # Status properties
    is_done = property(lambda x: x.status == x.STATUS_DONE)
    is_pending = property(lambda x: x.status == x.STATUS_PENDING)
    is_waiting = property(lambda x: x.status == x.STATUS_WAITING)
    is_invalid = property(lambda x: x.status == x.STATUS_INVALID)

    @property
    def is_correct(self):
        if self.given_grade is None:
            raise AttributeError('accessing attribute of non-graded response.')
        else:
            return self.given_grade == 100

    # Delegate properties
    activity = delegate_to('response')
    activity_id = delegate_to('response')
    activity_page = delegate_to('response')
    activity_page_id = delegate_to('response')
    user = delegate_to('response')
    user_id = delegate_to('response')

    @classmethod
    def response_data_hash(cls, response_data):
        """
        Computes a hash for the response_data attribute.

        Data must be given as a JSON-like structure or as a string of JSON data.
        """

        if response_data:
            if isinstance(response_data, str):
                data = response_data
            else:
                data = json.dumps(response_data, default=json_default)
            return md5hash(data)
        return ''

    def __init__(self, *args, **kwargs):
        # Django is loading object from the database -- we step out the way
        if args and not kwargs:
            super().__init__(*args, **kwargs)
            return

        # We create the response_data and feedback_data manually always using
        # copies of passed dicts. We save these variables here, init object and
        # then copy this data to the initialized dictionaries
        response_data = kwargs.pop('response_data', None) or {}
        feedback_data = kwargs.pop('feedback_data', None) or {}

        # This part makes a Submission instance initialize from a user +
        # activity instead of requiring a response object. The response is
        # automatically created on demand.
        user = kwargs.pop('user', None)
        if 'response' in kwargs and user and user != kwargs['response'].user:
            response_user = kwargs['response'].user
            raise ValueError(
                'Inconsistent user definition: %s vs. %s' % (
                    user, response_user)
            )
        elif 'response' not in kwargs and user:
            try:
                activity = kwargs.pop('activity')
            except KeyError:
                raise TypeError(
                    '%s objects bound to a user must also provide an '
                    'activity parameter.' % type(self).__name__
                )
            else:
                # User-bound constructor tries to obtain the response object by
                # searching for an specific (user, activity) tuple.
                response, created = Response.objects.get_or_create(
                    user=user,
                    activity=activity
                )
                kwargs['response'] = response

        if 'context' in kwargs or 'activity' in kwargs:
            raise TypeError(
                'Must provide an user to instantiate a bound submission.'
            )
        super().__init__(*args, **kwargs)

        # Now that we have initialized the submission, we fill the data
        # passed in the response_data and feedback_data dictionaries.
        self.response_data = dict(self.response_data or {}, **response_data)
        self.feedback_data = dict(self.response_data or {}, **feedback_data)

    def __str__(self):
        if self.given_grade is None:
            grade = self.status
        else:
            grade = '%s pts' % self.final_grade
        user = self.user
        activity = self.activity
        name = self.__class__.__name__
        return '<%s: %s by %s (%s)>' % (name, activity, user, grade)

    def __html__(self):
        """
        A string of html source representing the feedback.
        """

        if self.is_done:
            data = {'grade': (self.final_grade or 0)}

            if self.final_grade == 100:
                return markdown(self.MESSAGE_OK)
            elif self.given_grade == 100:
                return markdown(self.ok_with_penalties_message)
            elif not self.given_grade:
                return markdown(self.MESSAGE_WRONG)
            else:
                return markdown(self.MESSAGE_PARTIAL % data)
        else:
            return markdown(self.MESSAGE_NOT_GRADED)

    def save(self, *args, **kwargs):
        if not self.response_hash:
            self.response_hash = self.response_hash_from_data(
                self.response_hash)
        super().save(*args, **kwargs)

    def feedback(self, commit=True, force=False, silent=False):
        """
        Return the feedback object associated to the given response.

        This method may trigger the autograde() method, if grading was not
        performed yet. If you want to defer database access, call it with
        commit=False to prevent saving any modifications to the response object
        to the database.

        The commit, force and silent arguments have the same meaning as in
        the :func:`Submission.autograde` method.
        """

        if self.status == self.STATUS_PENDING:
            self.autograde(commit=commit, force=force, silent=silent)
        elif self.status == self.STATUS_INVALID:
            raise self.feedback_data
        elif self.status == self.STATUS_WAITING:
            return None
        return self.feedback_data

    def autograde(self, commit=True, force=False, silent=False):
        """
        Performs automatic grading.

        Response subclasses must implement the autograde_compute() method in
        order to make automatic grading work. This method may write any
        relevant information to the `feedback_data` attribute and must return
        a numeric value from 0 to 100 with the given automatic grade.

        Args:
            commit:
                If false, prevents saving the object when grading is complete.
                The user must save the object manually after calling this
                method.
            force:
                If true, force regrading the item even if it has already been
                graded. The default behavior is to ignore autograde from a
                graded submission.
            silent:
                Prevents the autograde_signal from triggering in the end of
                a successful autograde.
        """

        if self.status == self.STATUS_PENDING or force:
            try:
                value = self.autograde_value()
            except self.InvalidResponseError as ex:
                self.status = self.STATUS_INVALID
                self.feedback_data = ex
                self.given_grade = self.final_grade = decimal.Decimal(0)
                if commit:
                    self.save()
                raise

            if value is None:
                self.status = self.STATUS_WAITING
            else:
                self.given_grade = decimal.Decimal(value)
                if self.final_grade is None:
                    self.final_grade = self.given_grade
                self.status = self.STATUS_DONE
                if not silent:
                    autograde_signal.send_robust(
                        self.__class__,
                        response_item=self,
                        given_grade=self.given_grade
                    )
            if commit and self.pk:
                self.save(update_fields=['status', 'feedback_data',
                                         'given_grade', 'final_grade'])
            elif commit:
                self.save()

        elif self.status == self.STATUS_INVALID:
            raise self.feedback_data

    def manual_grade(self, grade, commit=True, raises=False, silent=False):
        """
        Saves result of manual grading.

        Args:
            grade (number):
                Given grade, as a percentage value.
            commit:
                If false, prevents saving the object when grading is complete.
                The user must save the object manually after calling this
                method.
            raises:
                If submission has already been graded, raises a GradingError.
            silent:
                Prevents the manual_grade_signal from triggering in the end of
                a successful autograde.
        """

        if self.status != self.STATUS_PENDING and raises:
            raise GradingError(
                'Submission has already been graded!'
            )

        raise NotImplementedError('TODO')

    def autograde_value(self):
        """
        This method should be implemented in subclasses.
        """

        raise ImproperlyConfigured(
            'Response subclass %r must implement the autograde_value().'
            'This method should perform the automatic grading and return the '
            'resulting grade. Any additional relevant feedback data might be '
            'saved to the `feedback_data` attribute, which is then is pickled '
            'and saved into the database.' % type(self).__name__
        )

    def regrade(self, method, commit=True):
        """
        Recompute the grade for the given submission.

        If status != 'done', it simply calls the .autograde() method. Otherwise,
        it accept different strategies for updating to the new grades:
            'update':
                Recompute the grades and replace the old values with the new
                ones. Only saves the submission if the feedback_data or the
                given_grade attributes change.
            'best':
                Only update if the if the grade increase.
            'worst':
                Only update if the grades decrease.
            'best-feedback':
                Like 'best', but updates feedback_data even if the grades
                change.
            'worst-feedback':
                Like 'worst', but updates feedback_data even if the grades
                change.

        Return a boolean telling if the regrading was necessary.
        """
        if self.status != self.STATUS_DONE:
            return self.autograde()

        # We keep a copy of the state, if necessary. We only have to take some
        # action if the state changes.
        def rollback():
            self.__dict__.clear()
            self.__dict__.update(state)

        state = self.__dict__.copy()
        self.autograde(force=True, commit=False)

        # Each method deals with the new state in a different manner
        if method == 'update':
            if state != self.__dict__:
                if commit:
                    self.save()
                return False
            return True
        elif method in ('best', 'best-feedback'):
            if self.given_grade <= state.get('given_grade', 0):
                new_feedback_data = self.feedback_data
                rollback()
                if new_feedback_data != self.feedback_data:
                    self.feedback_data = new_feedback_data
                    if commit:
                        self.save()
                    return True
                return False
            elif commit:
                self.save()
            return True

        elif method in ('worst', 'worst-feedback'):
            if self.given_grade >= state.get('given_grade', 0):
                new_feedback_data = self.feedback_data
                rollback()
                if new_feedback_data != self.feedback_data:
                    self.feedback_data = new_feedback_data
                    if commit:
                        self.save()
                    return True
                return False
            elif commit:
                self.save()
            return True
        else:
            rollback()
            raise ValueError('invalid method: %s' % method)


class InvalidResponseError(Exception):
    """Raised by compute_response() when the response is invalid."""


# Save a copy in the class namespace for convenience
Submission.InvalidResponseError = InvalidResponseError


def md5hash(st):
    """Compute the hex-md5 hash of string.

    Returns a string of 32 ascii characters."""

    return hashlib.md5(st.encode('utf8')).hexdigest()


@singledispatch
def json_default(x):
    raise TypeError('Not a JSON-compatible type: %s' % type(x).__name__)


@json_default.register(Decimal)
def _(x):
    return str(x)
