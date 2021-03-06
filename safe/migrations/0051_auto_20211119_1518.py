# Generated by Django 3.2.4 on 2021-11-19 15:18

from django.db import migrations, models
import django.db.models.deletion
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0050_installment'),
    ]

    operations = [
        migrations.CreateModel(
            name='Instalment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', django_fsm.FSMField(choices=[('pending', 'Pending'), ('active', 'Active'), ('creation_failed', 'CreationFailed'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('errored', 'Errored')], default='pending', max_length=50, protected=True)),
                ('external_id', models.TextField(blank=True, null=True)),
                ('name', models.TextField()),
                ('payment_method', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='installment', to='safe.paymentmethod')),
                ('safe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='installment', to='safe.safe')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.DeleteModel(
            name='Installment',
        ),
    ]
