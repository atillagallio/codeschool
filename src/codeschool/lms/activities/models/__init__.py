from .managers import *
from .activity import Activity
from .activity_list import ActivityList, ActivitySection
from .response import Response
from .submission import Submission


def register_submission_class(activity_class):
    """
    Decorator for a ResponseItem subclass that register a given ResponseItem
    class to the class associated with the decorated Question class.
    """

    if not issubclass(activity_class, Activity):
        raise TypeError('expect an Activity subclass')

    def decorator(cls):
        if not issubclass(cls, Submission):
            raise TypeError('expect a ResponseItem subclasss')

        activity_class.submission_class = cls
        return cls

    return decorator
