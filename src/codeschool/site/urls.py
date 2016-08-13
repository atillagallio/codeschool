"""server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
import django.contrib.admin
from codeschool.auth.views import index_view, profile_view
from codeschool.lms.activities.views import main_activity_list

urlpatterns = [
    # Basic URLS
    url(r'^_admin/', django.contrib.admin.site.urls),
    url(r'^admin/', include('wagtail.wagtailadmin.urls')),
    url(r'^$', index_view),
    url(r'^profile/$', profile_view, name='profile-view'),

    # Codeschool Apps
    url(r'^auth/', include('codeschool.auth.urls', namespace='auth')),
    url('', include('social.apps.django_app.urls', namespace='social')),

    # Global dashboard
    url(r'^activities/$', main_activity_list, name='main-activity-list'),

    # Wagtail endpoint
    url(r'', include('wagtail.wagtailcore.urls')),
]
