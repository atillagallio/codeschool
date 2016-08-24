# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-06 17:42
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.manager
import wagtail_model_tools.models.mixins
import wagtail_model_tools.models.singlepage


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('wagtailcore', '0002_initial_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileFormat',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ref', models.CharField(max_length=10, unique=True)),
                ('name', models.CharField(max_length=140)),
                ('comments', models.TextField(blank=True)),
                ('is_binary', models.BooleanField(default=False)),
                ('is_language', models.BooleanField(default=False)),
                ('is_supported', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='HiddenRoot',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=(wagtail_model_tools.models.mixins.ProxyPageMixin, wagtail_model_tools.models.singlepage.SinglePageMixin, 'wagtailcore.page'),
            managers=[
                ('_default_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='RogueRoot',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=(wagtail_model_tools.models.mixins.ProxyPageMixin, wagtail_model_tools.models.singlepage.SinglePageMixin, 'wagtailcore.page'),
            managers=[
                ('_default_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='ProgrammingLanguage',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('core.fileformat',),
        ),
    ]
