# Generated by Django 3.2.4 on 2021-07-20 13:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0022_auto_20210720_1333'),
    ]

    operations = [
        migrations.AlterField(
            model_name='doozeztask',
            name='job',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='jobs_tasks', to='safe.doozezjob'),
        ),
    ]