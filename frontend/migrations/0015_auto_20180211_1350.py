# Generated by Django 2.0.1 on 2018-02-11 13:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0014_file_error_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='file',
            name='hash_value',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
    ]
