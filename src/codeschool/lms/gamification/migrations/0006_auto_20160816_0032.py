# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-16 03:32
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gamification', '0005_auto_20160814_2207'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userscore',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='userscore',
            unique_together=set([('user', 'page')]),
        ),
    ]
