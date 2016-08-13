from django.dispatch import receiver

from codeschool.lms.activities.signals import autograde_signal
from codeschool.lms.gamification.models import PblUser, category_from_response, \
    Action, register_points


@receiver(autograde_signal)
def my_handle(given_grade, response_item, **kwargs):
    # print('autograde!', response_item.activity)
    try:
        pbl_user = response_item.user.pbl_user
    except PblUser.DoesNotExist:
        pbl_user = PblUser.objects.create(user=response_item.user)

    category = category_from_response(response_item)

    a = response_item.activity
    actions = Action.objects.filter(activity=a)

    for action in actions:
        register_points(pbl_user, action, category)
        # response_item.response grupo de reponse itens do mesmo usuário e da mesma atividade
        # response.itens é o manager do django.

        # register_points(response.user, response.activity, category)