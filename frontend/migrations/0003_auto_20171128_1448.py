# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-28 14:48
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0002_programm'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Programm',
            new_name='Program',
        ),
    ]
