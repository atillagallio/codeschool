# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-13 21:14
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0006_auto_20160812_2120'),
    ]

    operations = [
        migrations.RenameField(
            model_name='formquestion',
            old_name='points_value',
            new_name='points_total',
        ),
        migrations.RenameField(
            model_name='formquestion',
            old_name='stars_value',
            new_name='stars_total',
        ),
    ]