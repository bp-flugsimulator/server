# Generated by Django 2.0.2 on 2018-03-28 08:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0004_auto_20180327_1514'),
    ]

    operations = [
        migrations.AlterField(
            model_name='programstatus',
            name='start_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]