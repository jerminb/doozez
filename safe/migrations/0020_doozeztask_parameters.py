# Generated by Django 3.2.4 on 2021-07-15 12:42

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0019_auto_20210714_2014'),
    ]

    operations = [
        migrations.AddField(
            model_name='doozeztask',
            name='parameters',
            field=jsonfield.fields.JSONField(null=True),
        ),
    ]