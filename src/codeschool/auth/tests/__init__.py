from codeschool.tests import *
from codeschool.auth.factories import UserFactory


@pytest.fixture
def password():
    """A random password."""

    return fake.password()


@pytest.fixture
def user():
    """A simple user account (no valid password)"""

    return UserFactory.create()


@pytest.fixture
def user_with_password(password):
    """
    User account with password (use together with the password fixture).
    """

    user = UserFactory.create(password=None)
    user.set_password(password)
    user.save()
    return user

