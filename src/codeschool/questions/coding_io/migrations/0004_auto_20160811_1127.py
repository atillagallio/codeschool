# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-11 14:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coding_io', '0003_auto_20160806_1512'),
    ]

    operations = [
        migrations.RenameField(
            model_name='codingioquestion',
            old_name='import_object_from',
            new_name='import_file',
        ),
        migrations.AddField(
            model_name='codingioquestion',
            name='is_imported_question',
            field=models.BooleanField(default=bool),
        ),
    ]