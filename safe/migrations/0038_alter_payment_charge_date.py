# Generated by Django 3.2.4 on 2021-08-30 17:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0037_alter_payment_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='charge_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]