# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-13 00:00
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gamification', '0002_auto_20160812_2041'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='TotalScores',
            new_name='TotalScore',
        ),
        migrations.AlterUniqueTogether(
            name='totalscore',
            unique_together=set([('page',)]),
        ),
    ]
