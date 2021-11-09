# Generated by Django 3.2.4 on 2021-11-01 15:44

from django.db import migrations
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0046_alter_participation_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentmethod',
            name='status',
            field=django_fsm.FSMField(choices=[('PEA', 'PendingExternalApproval'), ('EAS', 'ExternalApprovalSuccessful'), ('EAF', 'ExternalApprovalFailed'), ('EXC', 'ExternallyCreated'), ('EXS', 'ExternallySubmitted'), ('EXA', 'ExternallySubmitted')], default='PEA', max_length=50, protected=True),
        ),
    ]