# Generated by Django 2.0.1 on 2018-01-21 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0004_auto_20180121_0622'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='slavestatus',
            name='slave',
        ),
        migrations.AddField(
            model_name='slave',
            name='command_uuid',
            field=models.CharField(max_length=32, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='slave',
            name='online',
            field=models.BooleanField(default=False),
        ),
        migrations.DeleteModel(
            name='SlaveStatus',
        ),
    ]
