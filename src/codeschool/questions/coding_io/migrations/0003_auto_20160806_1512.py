# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-06 18:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coding_io', '0002_auto_20160806_1451'),
    ]

    operations = [
        migrations.AlterField(
            model_name='codingioquestion',
            name='difficulty',
            field=models.IntegerField(blank=True, choices=[(0, 'Trivial'), (1, 'Very Easy'), (2, 'Easy'), (3, 'Regular'), (4, 'Hard'), (5, 'Very Hard'), (6, 'Challenge!')]),
        ),
        migrations.AlterField(
            model_name='codingioquestion',
            name='points_value',
            field=models.IntegerField(blank=True, help_text='Points are awarded in specific contexts (e.g., associated with a quiz or in a list of activities) and can be used to compute grades in a flexible way.', verbose_name='value'),
        ),
        migrations.AlterField(
            model_name='codingioquestion',
            name='score_value',
            field=models.IntegerField(blank=True, help_text='The score this function is worth in Codeschool generic ranking system. This score is used in the site leaderboard and solely as a motivation for students to engage in activities. The default score is 100 per activity.', verbose_name='maximum score'),
        ),
        migrations.AlterField(
            model_name='codingioquestion',
            name='stars_value',
            field=models.FloatField(blank=True, default=0.0, help_text='Number of stars the activity is worth (fractional stars are accepted). Stars are optional bonus points for special accomplishments that can be used to trade "special powers" in codeschool.', verbose_name='stars'),
        ),
    ]
