# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-15 01:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0007_auto_20160812_2041'),
    ]

    operations = [
        migrations.AddField(
            model_name='response',
            name='is_correct',
            field=models.BooleanField(default=bool),
        ),
        migrations.AddField(
            model_name='response',
            name='is_finished',
            field=models.BooleanField(default=bool),
        ),
    ]