# Generated by Django 2.0.1 on 2018-01-08 20:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0003_auto_20180108_2005'),
    ]

    operations = [
        migrations.CreateModel(
            name='SlaveStatus',
            fields=[
                ('slave',
                 models.OneToOneField(
                     on_delete=django.db.models.deletion.CASCADE,
                     primary_key=True,
                     serialize=False,
                     to='frontend.Slave')),
                ('command_uuid', models.CharField(max_length=32, unique=True)),
                ('online', models.BooleanField(default=False)),
            ],
        ),
        migrations.RemoveField(
            model_name='slaveonlinerequest',
            name='slave',
        ),
        migrations.RemoveField(
            model_name='slave',
            name='online',
        ),
        migrations.DeleteModel(name='SlaveOnlineRequest', ),
    ]
