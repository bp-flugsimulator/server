# Generated by Django 2.0.1 on 2018-01-25 12:39

from django.db import migrations, models
import frontend.models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0006_remove_slavestatus_dummy'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='command_uuid',
            field=models.CharField(
                blank=True, max_length=32, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='file',
            name='moved',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='file',
            name='destination_path',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='file',
            name='source_path',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='program',
            name='arguments',
            field=models.TextField(
                blank=True,
                validators=[frontend.models.validate_argument_list]),
        ),
        migrations.AlterField(
            model_name='program',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='program',
            name='path',
            field=models.TextField(),
        ),
    ]
