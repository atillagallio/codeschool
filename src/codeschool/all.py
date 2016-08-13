"""
Import most models and useful function into the same namespace. Should be used
only in the cli.
"""

from codeschool.models import *
from codeschool.core.models import *
from codeschool.auth.models import *
from codeschool.lms.activities.models import *
from codeschool.lms.gamification.models import *
from codeschool.questions.models import *
from codeschool.questions.coding_io.models import *
from codeschool.questions.form.models import *
