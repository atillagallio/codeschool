"""
Generic tests for all activity sub-classes.
"""
import pytest
from . import activity_section, activity_section_db


@pytest.mark.django_db
def test_activity_do_full_clean(activity):
    activity.full_clean(exclude=['depth', 'path'])


@pytest.mark.django_db
def test_create_activity_from_minimum_parameters(activity_section_db, activity):
    activity_section_db.add_child(instance=activity)
