# Generated by Django 2.0.3 on 2018-03-25 21:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0002_auto_20180310_1715'),
    ]

    operations = [
        migrations.AddField(
            model_name='programstatus',
            name='start_time',
            field=models.DateTimeField(default=0),
        ),
    ]