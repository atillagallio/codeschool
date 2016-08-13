from codeschool import models


class ResponseDataMixin(models.Model):
    """
    Mixin that adds response data for several fields stored in a JSON
    dictionary.
    """

    class Meta:
        abstract = True

    response_data = models.JSONField(
        null=True,
        blank=True,
    )
    response_hash = models.CharField(
        max_length=32,
        blank=True,
    )


class FeedbackDataMixin(models.Model):
    """
    Mixin that adds feedback data for several fields stored in a JSON
    dictionary.
    """

    class Meta:
        abstract = True

    feedback_data = models.JSONField(
        null=True,
        blank=True,
    )


def data_property(name, func=None, data_attr=None):
    pass


def feedback_property(name, func=None):
    return data_property(name, func, data_attr='feedback_data')


def response_property(name, func=None):
    return data_property(name, func, data_attr='response_data')
