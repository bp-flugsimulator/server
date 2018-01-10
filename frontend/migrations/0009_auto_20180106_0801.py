# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-06 08:01
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0008_auto_20180105_1004'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScriptGraphFiles',
            fields=[
                ('id',
                 models.AutoField(
                     auto_created=True,
                     primary_key=True,
                     serialize=False,
                     verbose_name='ID')),
                ('index', models.IntegerField()),
                ('file',
                 models.ForeignKey(
                     on_delete=django.db.models.deletion.CASCADE,
                     to='frontend.File')),
            ],
        ),
        migrations.CreateModel(
            name='ScriptGraphPrograms',
            fields=[
                ('id',
                 models.AutoField(
                     auto_created=True,
                     primary_key=True,
                     serialize=False,
                     verbose_name='ID')),
                ('index', models.IntegerField()),
                ('program',
                 models.ForeignKey(
                     on_delete=django.db.models.deletion.CASCADE,
                     to='frontend.Program')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='script',
            unique_together=set([]),
        ),
        migrations.AddField(
            model_name='scriptgraphprograms',
            name='script',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='frontend.Script'),
        ),
        migrations.AddField(
            model_name='scriptgraphfiles',
            name='script',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='frontend.Script'),
        ),
        migrations.RemoveField(
            model_name='script',
            name='payload',
        ),
        migrations.RemoveField(
            model_name='script',
            name='slave',
        ),
        migrations.AlterUniqueTogether(
            name='scriptgraphprograms',
            unique_together=set([('script', 'index', 'program')]),
        ),
        migrations.AlterUniqueTogether(
            name='scriptgraphfiles',
            unique_together=set([('script', 'index', 'file')]),
        ),
    ]
