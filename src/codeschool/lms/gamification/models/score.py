from collections import Counter

from django.utils.translation import ugettext_lazy as _
from lazyutils import lazy, lazy_classattribute

from codeschool import models


class ScoreHandler(models.TimeStampedModel):
    """
    Common implementations for TotalScores and UserScores.
    """

    class Meta:
        abstract = True

    page = models.ForeignKey(models.Page, related_name='+')
    points = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    stars = models.FloatField(default=0.0)

    @lazy_classattribute
    def _wagtail_root(cls):
        return models.Page.objects.get(path='0001')

    @lazy
    def specific(self):
        return self.page.specific

    def get_parent(self):
        """
        Return parent resource handler.
        """

        raise NotImplementedError('must be implemented in subclasses')

    def get_children(self):
        """
        Return a queryset with all children resource handlers.
        """

        raise NotImplementedError('must be implemented in subclasses')

    def set_diff(self, points=0, score=0, stars=0, propagate=True, commit=True):
        """
        Change the given resources by the given amounts and propagate to all
        the parents.
        """

        # Update fields
        fields = []
        if points:
            fields.append('points')
            self.points += points
        if score:
            self.score += score
            fields.append('score')
        if stars:
            self.stars += stars
            fields.append('stars')

        if fields and commit:
            self.save(update_fields=fields)

        # Propagate to all parent resources
        if propagate and fields and commit:
            parent = self.get_parent()
            if parent is not None:
                parent.set_diff(points, score, stars, propagate)

    def set_values(self, points=0, score=0, stars=0, propagate=True,
                   optimistic=False, commit=True):
        """
        Register a new value for the resource.

        If new value is greater than the current value, update the resource
        and propagate.

        Args:
            points, score, stars, (number):
                New value assigned to each specified resource.
            propagate (bool):
                If True (default), increment all parent nodes.
            optimistic (bool):
                If True, only update if give value is greater than the
                registered value.
            commit (bool):
                If True (default), commit results to the database.
        """

        d_points = points - self.points
        d_score = score - self.score
        d_stars = stars - self.stars
        if optimistic:
            d_points = max(d_points, 0)
            d_score = max(d_score, 0)
            d_stars = max(d_stars, 0)

        self.set_diff(points=d_points, score=d_score, stars=d_stars,
                      propagate=propagate, commit=commit)


class TotalScore(ScoreHandler):
    """
    Stores the maximum amount of resources that can be associated with each
    page.

    Resources can be score, points, or stars.
    """

    class Meta:
        unique_together = [('page',)]

    @lazy
    def total_attribute_name(self):
        return self.resource_name + '_value'

    @lazy
    def resource_name(self):
        return self.__class__.__name__.lower()[:-5]

    @classmethod
    def load(cls, page):
        """
        Return TotalScore object for the given page.
        """

        score, created = cls.objects.get_or_create(page=page)
        return score

    @classmethod
    def update(cls, page, **kwargs):
        """
        Updates the total resources of the given user/page pair.

        Accept the same keyword arguments as the .set_values() method.
        """

        score = cls.load(page)
        score.set_values(**kwargs)

    def get_parent(self):
        parent_page = self.page.get_parent()
        if parent_page is None:
            return None

        return self.__class__.objects.get_or_create(page=parent_page)[0]

    def get_children(self):
        children_pages = self.page.get_children()
        return [self.load(page) for page in children_pages]

    def contribution(self):
        """
        Return the contribution of the current page to the resource total.
        """

        data = Counter()
        if hasattr(self.specific, 'get_score_contributions'):
            data.update(self.specific.get_score_contributions())
        return data

    def recompute_total(self, commit=True):
        """
        Recompute the totals for the given activity and all of its children.

        Set commit=False to prevent modifying the database.
        """

        initial = self.contribution()
        totals = [c.recompute_total(commit) for c in self.get_children()]
        result = sum(totals, initial)
        if commit:
            fields = []
            for k, v in result.items():
                fields.append(k)
                setattr(self, k, v)
            self.save(update_fields=fields)
        return result


class UserScores(ScoreHandler):
    """
    Base class for all accumulated resources.
    """

    used_stars = models.FloatField(default=0.0)
    user = models.OneToOneField(models.User, related_name='+')

    @property
    def available_stars(self):
        return self.stars - self.used_stars

    @available_stars.setter
    def available_stars(self, value):
        self.used_stars = self.stars - value

    @classmethod
    def load(cls, user, page):
        """
        Return UserScore object for the given user/page.
        """
        score, created = cls.objects.get_or_create(user=user, page=page)
        return score

    @classmethod
    def update(cls, user, page, **kwargs):
        """
        Updates the accumulated resources of the given user/page pair.

        Accept the same keyword arguments as the .set_values() method.
        """

        score = cls.load(user, page)
        score.set_values(**kwargs)

    @classmethod
    def total_score(cls, user):
        """
        Return the total score for the given user.

        This is equivalent to the score associated with wagtail's root page.
        """

        return cls.objects.get_or_create(user=user, page=cls._wagtail_root)[0]

    def get_parent(self):
        parent_page = self.page.get_parent()
        if parent_page is None:
            return None

        return self.__class__.objects.get_or_create(user=self.user,
                                                    page=parent_page)[0]

    def get_children(self):
        children_pages = self.page.get_children()
        return [self.load(self.user, page) for page in children_pages]


class HasScorePage(models.Page):
    """
    Mixin abstract page class for Page elements that implement the Score API.

    Subclasses define points_value, stars_value, and difficulty fields that
    define how activities contribute to Codeschool score system.
    """

    class Meta:
        abstract = True

    DIFFICULTY_TRIVIAL = 0
    DIFFICULTY_VERY_EASY = 1
    DIFFICULTY_EASY = 2
    DIFFICULTY_REGULAR = 3
    DIFFICULTY_HARD = 4
    DIFFICULTY_VERY_HARD = 5
    DIFFICULTY_CHALLENGE = 6
    DIFFICULTY_CHOICES = [
        (DIFFICULTY_TRIVIAL, _('Trivial')),
        (DIFFICULTY_VERY_EASY, _('Very Easy')),
        (DIFFICULTY_EASY, _('Easy')),
        (DIFFICULTY_REGULAR, _('Regular')),
        (DIFFICULTY_HARD, _('Hard')),
        (DIFFICULTY_VERY_HARD, _('Very Hard')),
        (DIFFICULTY_CHALLENGE, _('Challenge!')),
    ]
    SCORE_FROM_DIFFICULTY = {
        DIFFICULTY_TRIVIAL: 10,
        DIFFICULTY_VERY_EASY: 30,
        DIFFICULTY_EASY: 60,
        DIFFICULTY_REGULAR: 100,
        DIFFICULTY_HARD: 150,
        DIFFICULTY_VERY_HARD: 250,
        DIFFICULTY_CHALLENGE: 500,
    }
    DEFAULT_DIFFICULTY = DIFFICULTY_REGULAR

    points_value = models.IntegerField(
        _('value'),
        blank=True,
        help_text=_(
            'Points may be awarded in specific contexts (e.g., associated with '
            'a quiz or in a list of activities) and in Codeschool\'s generic '
            'ranking system.'
        )
    )
    stars_value = models.FloatField(
        _('stars'),
        blank=True,
        help_text=_(
            'Number of stars the activity is worth (fractional stars are '
            'accepted). Stars are optional bonus points for special '
            'accomplishments that can be used to trade "special powers" in '
            'codeschool.'
        ),
        default=0.0
    )
    difficulty = models.IntegerField(
        blank=True,
        choices=DIFFICULTY_CHOICES,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not kwargs:
            self._score_memo = self.points_value, self.stars_value

    def clean_fields(self, exclude=None):
        # Fill default difficulty
        if self.difficulty is None:
            if exclude is None or 'difficulty' not in exclude:
                self.difficulty = self.DEFAULT_DIFFICULTY

        # Fill default points value from difficulty
        if self.points_value is None:
            if exclude is None or 'exclude' not in exclude:
                self.points_value = self.SCORE_FROM_DIFFICULTY[self.difficulty]

        super().clean_fields(exclude=exclude)

    def save(self, *args, **kwargs):
        points, stars = getattr(self, '_score_memo', (0, 0))
        super().save(*args, **kwargs)

        # Update the ScoreTotals table, if necessary.
        if stars != self.stars_value or points != self.points_value:
            score = self.get_score_from_points(self.points_value)
            TotalScore.update(
                self,
                points=self.points_value,
                stars=self.stars_value,
                score=score,
            )

    def get_score_contributions(self):
        """
        Return a dictionary with the score value associated with
        points, score, and stars.
        """

        return {
            'points': self.points_value,
            'stars': self.stars_value,
            'score': self.get_score_from_points(self.points_value),
        }

    def get_score_from_points(self, points):
        """
        Compute score value from total number of points.

        The default implementation simply return the argument. Business logic
        may require a different relationship between score and point values.
        """
        return points

