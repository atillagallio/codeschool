import factory.django
from django.db.models import signals
from mommys_boy import DjangoMommyFactory, SubFactory, Faker

from codeschool.auth import models


@factory.django.mute_signals(signals.pre_save, signals.post_save)
class UserFactory(DjangoMommyFactory):
    class Meta:
        model = models.User
        recipe = 'global'


class FullUserFactory(DjangoMommyFactory):
    class Meta:
        model = models.User
        recipe = 'global'


class ProfileFactory(DjangoMommyFactory):
    class Meta:
        model = models.Profile

    user = SubFactory(UserFactory)
    phone = Faker('phone_number')
    path = None
    depth = None
    url_path = None

