"""
Generic tests that any question type should pass.

The functions in this module should be imported within each question type test
module.
"""
from codeschool.lms.activities.tests import *
from codeschool.lms.activities.tests.generic import *


@pytest.fixture
def activity(question):
    return question


