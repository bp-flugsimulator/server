# Generated by Django 2.0.2 on 2018-03-10 17:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='filesystem',
            name='source_type',
            field=models.CharField(
                choices=[('file', 'File'), ('dir', 'Directory')],
                default='file',
                max_length=4),
        ),
    ]
