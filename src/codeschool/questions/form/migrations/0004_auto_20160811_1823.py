# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-11 21:23
from __future__ import unicode_literals

import codeschool.vendor.wagtailmarkdown.blocks
from django.db import migrations
import wagtail.wagtailcore.blocks
import wagtail.wagtailcore.fields


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0003_auto_20160811_1127'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formquestion',
            name='body',
            field=wagtail.wagtailcore.fields.StreamField((('paragraph', wagtail.wagtailcore.blocks.RichTextBlock()), ('heading', wagtail.wagtailcore.blocks.CharBlock(classname='full title')), ('markdown', codeschool.vendor.wagtailmarkdown.blocks.MarkdownBlock()), ('html', wagtail.wagtailcore.blocks.RawHTMLBlock())), blank=True, help_text='Describe what the question is asking and how should the students answer it as clearly as possible. Good questions should not be ambiguous.', null=True, verbose_name='Question description'),
        ),
    ]