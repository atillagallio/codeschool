"""
Important singleton pages for a codeschool installation.
"""
import model_reference
from django.utils.translation import ugettext_lazy as _
from codeschool import models


class HiddenRoot(models.ProxyPageMixin, models.SinglePageMixin, models.Page):
    """
    A page representing the site's root page
    """

    class Meta:
        proxy = True

    @classmethod
    def get_state(cls):
        return {
            'title': _('Hidden pages'),
            'locked': True,
            'slug': 'hidden'
        }

    @classmethod
    def get_parent(cls):
        return models.Page.objects.get(path='0001')


class RogueRoot(models.ProxyPageMixin, models.SinglePageMixin, models.Page):
    """
    A page representing the site's root page
    """

    class Meta:
        proxy = True

    @classmethod
    def get_state(cls):
        return {
            'title': _('Rogue pages'),
            'locked': True,
            'slug': 'rogue'
        }

    @classmethod
    def get_parent(cls):
        return HiddenRoot.objects.instance()


@model_reference.factory('root-page')
def wagtail_root_page():
    return models.Page.objects.get(path='00010001')