# Generated by Django 3.2.4 on 2022-09-30 12:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0055_rename_monthly_payment_product_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='participation',
            name='product',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='participation_product', to='safe.product'),
        ),
    ]
