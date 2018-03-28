# Generated by Django 2.0.2 on 2018-03-27 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0003_programstatus_start_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='filesystem',
            name='destination_type',
            field=models.CharField(choices=[('file', 'Rename'), ('dir', 'Keep Name')], default='file', max_length=4),
        ),
        migrations.AlterField(
            model_name='program',
            name='start_time',
            field=models.IntegerField(default=0),
        ),
    ]
