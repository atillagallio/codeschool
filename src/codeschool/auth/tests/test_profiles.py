from codeschool.auth.tests import *


@pytest.mark.django_db
def test_user_profile_is_created_automatically():
    user = UserFactory.create()
    assert user.profile is not None
