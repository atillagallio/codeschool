"""
Functions and fixtures that aids writing unit tests.
"""

import pytest
from sulfur import Driver as _sulfur_driver
from mommys_boy import mommy, fake


@pytest.fixture
def sulfur_wait():
    """The value that will be passed to the implicit wait parameter in
    selenium."""

    return 1


@pytest.fixture
def ui(selenium, live_server, sulfur_wait):
    """
    Return a initialized sulfur driver instance.

    The sulfur driver wraps selenium in a more convenient interface.
    """

    return _sulfur_driver(selenium, base_url=live_server.url, wait=sulfur_wait)


@pytest.fixture
def html(ui):
    """The dom attribute of a driver ui.

    It can be used to access elements in the page with defined ids. It is also
    useful for filling up forms as in the example::

        ... (open page)
        html.formButton.click()      # clicks the button with id="formButton"
        html.id_name = 'John'        # send the keys 'John' to the form element
        html['send-button'].click()  # alternative API for element whose id's are
                                     # not valid python names.
    """

    return ui.ids


@pytest.fixture
def soup(ui):
    """
    Beautiful soup accessor.
    """

    raise NotImplementedError


@pytest.fixture
def url_data(url_owner):
    return None


@pytest.fixture
def url_owner(user):
    return user


@pytest.fixture
def public_url(request):
    return request.param


@pytest.fixture
def login_url(request, user):
    return request.param.format(user=user)


