from mommys_boy import DjangoMommyFactory, SubFactory, Faker
from codeschool.auth import models


class UserFactory(DjangoMommyFactory):
    class Meta:
        model = models.User
        recipe = 'global'


class ProfileFactory(DjangoMommyFactory):
    class Meta:
        model = models.Profile

    user = SubFactory(UserFactory)
    phone = Faker('phone_number')