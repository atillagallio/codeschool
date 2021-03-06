# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-06 17:51
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import wagtail.contrib.wagtailroutablepage.models
import wagtail.wagtailcore.blocks
import wagtail.wagtailcore.fields
import wagtail.wagtaildocs.blocks
import wagtail.wagtailimages.blocks


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('wagtailcore', '0028_merge'),
    ]

    operations = [
        migrations.CreateModel(
            name='FormQuestion',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.Page')),
                ('short_description', models.CharField(help_text='A short textual description to be used in titles, lists, etc.', max_length=140, verbose_name='short description')),
                ('author_name', models.CharField(blank=True, help_text="The author's name, if not the same user as the question owner.", max_length=100, verbose_name="Author's name")),
                ('score_value', models.IntegerField(help_text='The score this function is worth in Codeschool generic ranking system. This score is used in the site leaderboard and solely as a motivation for students to engage in activities. The default score is 100 per activity.', verbose_name='maximum score')),
                ('points_value', models.IntegerField(help_text='Points are awarded in specific contexts (e.g., associated with a quiz or in a list of activities) and can be used to compute grades in a flexible way.', verbose_name='value')),
                ('stars_value', models.FloatField(default=0.0, help_text='Number of stars the activity is worth (fractional stars are accepted). Stars are optional bonus points for special accomplishments that can be used to trade "special powers" in codeschool.', verbose_name='stars')),
                ('difficulty', models.IntegerField(choices=[(0, 'Trivial'), (1, 'Very Easy'), (2, 'Easy'), (3, 'Regular'), (4, 'Hard'), (5, 'Very Hard'), (6, 'Challenge!')], default=2)),
                ('body', wagtail.wagtailcore.fields.StreamField((('paragraph', wagtail.wagtailcore.blocks.RichTextBlock()), ('heading', wagtail.wagtailcore.blocks.CharBlock(classname='full title')), ('markdown', wagtail.wagtailcore.blocks.CharBlock(classname='markdown'))), blank=True, help_text='Describe what the question is asking and how should the students answer it as clearly as possible. Good questions should not be ambiguous.', null=True, verbose_name='Question description')),
                ('comments', wagtail.wagtailcore.fields.RichTextField(blank=True, help_text='(Optional) Any private information that you want to associate to the question page.', verbose_name='Comments')),
                ('import_object_from', models.FileField(blank=True, help_text='Fill missing fields from question file. You can safely leave this blank and manually insert all question fields.', null=True, upload_to='question-imports', verbose_name='import question')),
                ('form_data', wagtail.wagtailcore.fields.StreamField((('content', wagtail.wagtailcore.blocks.StreamBlock((('description', wagtail.wagtailcore.blocks.RichTextBlock()), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock()), ('document', wagtail.wagtaildocs.blocks.DocumentChooserBlock()), ('page', wagtail.wagtailcore.blocks.PageChooserBlock())))),), help_text='You can insert different types of fields for the student answers. This works as a simple form that accepts any combination of thedifferent types of answer fields.', verbose_name='Fields')),
            ],
            options={
                'permissions': (('download_question', 'Can download question files'),),
                'abstract': False,
            },
            bases=(wagtail.contrib.wagtailroutablepage.models.RoutablePageMixin, 'wagtailcore.page', models.Model),
        ),
    ]
