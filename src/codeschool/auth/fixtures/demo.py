import os
from django.core import serializers


def load():
    base = os.path.dirname(__file__)

    # Load users and profiles
    fname = os.path.join(base, 'users-demo.yaml')
    with open(fname) as F:
        users = serializers.deserialize('yaml', F)
        for user in users:
            user.save()
