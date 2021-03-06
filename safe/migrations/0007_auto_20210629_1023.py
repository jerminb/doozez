# Generated by Django 3.2.4 on 2021-06-29 10:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0006_auto_20210628_2020'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentmethod',
            name='is_default',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='participation',
            name='win_sequence',
            field=models.PositiveIntegerField(null=True),
        ),
    ]
