# Generated by Django 3.2.4 on 2021-06-21 11:35

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0002_auto_20210617_2015'),
    ]

    operations = [
        migrations.AddField(
            model_name='safe',
            name='monthly_payment',
            field=models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0.0)]),
        ),
        migrations.AddField(
            model_name='safe',
            name='status',
            field=models.CharField(choices=[('PPT', 'PendingParticipants'), ('PDR', 'PendingDraw'), ('PEP', 'PendingEntryPayment'), ('ACT', 'Active'), ('CPT', 'Complete')], default='PPT', max_length=3),
        ),
        migrations.AddField(
            model_name='safe',
            name='total_participants',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='safe',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]