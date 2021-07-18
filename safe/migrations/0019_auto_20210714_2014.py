# Generated by Django 3.2.4 on 2021-07-14 20:14

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0018_doozeztask'),
    ]

    operations = [
        migrations.AddField(
            model_name='doozeztask',
            name='created_on',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='doozeztask',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
