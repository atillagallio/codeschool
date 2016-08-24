from codeschool.tests import *
from codeschool.lms.activities.models import ActivityList, ActivitySection


@pytest.fixture
def activity_section(base_page_location_kwargs):
    return ActivitySection(
        title=fake.sentence().strip('.'),
        short_description=fake.sentence(),
        **base_page_location_kwargs,
    )


@pytest.fixture
def activity_section_db(activity_section):
    activity_section.save()
    return activity_section
