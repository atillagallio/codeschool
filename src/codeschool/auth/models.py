import datetime

from lazyutils import delegate_to

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, ugettext as __

from userena.models import UserenaBaseProfile, UserenaBaseProfileManager
from annoying.functions import get_config

from codeschool import models
from codeschool import panels
from codeschool.models import User

strptime = datetime.datetime.strptime


@receiver(post_save, sender=models.User)
def create_profile_on_user_save(instance, created, **kwargs):
    user = instance
    if created and user.username != 'AnonymousUser':
        profile, _ = Profile.objects.get_or_create(user=user)
        if get_config('CODESCHOOL_USERNAME_IS_SCHOOL_ID', False):
            profile.school_id = user.username
        profile.save()


class ProfileQuerySet(models.PageQuerySet):
    """
    Manager for objects that are userena profiles + wagtail pages.
    """


class ProfileManager(UserenaBaseProfileManager, models.PageManager):
    """
    Manage objects that are both Wagtail pages and userena profiles.
    """

    queryset_class = ProfileQuerySet


class Profile(UserenaBaseProfile, models.Page):
    """
    Social information about users.
    """

    class Meta:
        permissions = (
            ('student', _('Can access/modify data visible to student\'s')),
            ('teacher', _('Can access/modify data visible only to Teacher\'s')),
        )

    user = models.OneToOneField(
        User,
        unique=True,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_('user'),
        related_name='profile',
    )
    school_id = models.CharField(
        _('school id'),
        help_text=_('Identification number in your school issued id card.'),
        max_length=50,
        blank=True,
        null=True)
    nickname = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    gender = models.SmallIntegerField(
        _('gender'),
        choices=[(0, _('male')), (1, _('female'))],
        blank=True,
        null=True
    )
    date_of_birth = models.DateField(
        _('date of birth'),
        blank=True,
        null=True
    )
    website = models.URLField(blank=True, null=True)
    about_me = models.RichTextField(blank=True, null=True)
    objects = ProfileManager()

    # Delegates and properties
    username = delegate_to('user', True)
    first_name = delegate_to('user')
    last_name = delegate_to('user')
    email = delegate_to('user')

    @property
    def short_description(self):
        return '%s (id: %s)' % (self.get_full_name_or_username(),
                                self.school_id)

    @property
    def age(self):
        if self.date_of_birth is None:
            return None
        today = timezone.now().date()
        birthday = self.date_of_birth
        years = today.year - birthday.year
        birthday = datetime.date(today.year, birthday.month, birthday.day)
        if birthday > today:
            return years - 1
        else:
            return years

    def __str__(self):
        if self.user is None:
            return __('Unbound profile')
        full_name = self.user.get_full_name() or self.user.username
        return __('%(name)s\'s profile') % {'name': full_name}

    def save(self, *args, **kwargs):
        user = self.user
        if not self.title:
            self.title = self.title or __("%(name)s's profile") % {
                'name': user.get_full_name() or user.username
            }
        if not self.slug:
            self.slug = user.username.replace('.', '-')

        # Set parent page, if necessary
        if not self.path:
            root = ProfileList.objects.instance()
            root.add_child(instance=self)
        else:
            super().save(*args, **kwargs)

    def get_full_name_or_username(self):
        name = self.user.get_full_name()
        if name:
            return name
        else:
            return self.user.username

    # Serving pages
    template = 'cs_auth/profile-detail.jinja2'

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context['profile'] = self
        return context

    # Wagtail admin
    parent_page_types = ['ProfileList']
    content_panels = models.Page.content_panels + [
        panels.MultiFieldPanel([
            panels.FieldPanel('school_id'),
        ], heading='Required information'),
        panels.MultiFieldPanel([
            panels.FieldPanel('nickname'),
            panels.FieldPanel('phone'),
            panels.FieldPanel('gender'),
            panels.FieldPanel('date_of_birth'),
        ], heading=_('Personal Info')),
        panels.MultiFieldPanel([
            panels.FieldPanel('website'),
        ], heading=_('Web presence')),
        panels.RichTextFieldPanel('about_me'),
    ]


class ProfileList(models.ProxyPageMixin, models.SinglePageMixin, models.Page):
    """
    Root page representing the parent node for all user profiles.
    """

    class Meta:
        proxy = True

    @classmethod
    def get_state(cls):
        return {
            'title': _('List of users'),
            'slug': 'users',
        }

    # Serving pages
    template = 'page-list.jinja2'

    # Wagtail admin
    subpage_types = ['cs_auth.Profile']
    parent_page_types = ['wagtailcore.Page']
