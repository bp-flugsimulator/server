# Generated by Django 2.0.1 on 2018-01-25 15:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0007_auto_20180125_1239'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='file',
            name='moved',
        ),
        migrations.AddField(
            model_name='file',
            name='hash_value',
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
    ]
