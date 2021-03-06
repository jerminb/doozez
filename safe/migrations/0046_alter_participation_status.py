# Generated by Django 3.2.4 on 2021-10-26 14:09

from django.db import migrations
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0045_auto_20211012_1422'),
    ]

    operations = [
        migrations.AlterField(
            model_name='participation',
            name='status',
            field=django_fsm.FSMField(choices=[('PND', 'Pending'), ('ACT', 'Active'), ('CPT', 'Complete'), ('PPT', 'PendingPayment'), ('LEF', 'Left')], default='ACT', max_length=50, protected=True),
        ),
    ]
