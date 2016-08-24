from . import *


@pytest.mark.django_db
def test_create_activity_section_page():
    activity = activity_section(base_page_location_kwargs())