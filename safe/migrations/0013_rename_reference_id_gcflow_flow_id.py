# Generated by Django 3.2.4 on 2021-07-09 21:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0012_gcflow'),
    ]

    operations = [
        migrations.RenameField(
            model_name='gcflow',
            old_name='reference_id',
            new_name='flow_id',
        ),
    ]
