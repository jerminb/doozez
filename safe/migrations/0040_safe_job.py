# Generated by Django 3.2.4 on 2021-09-15 14:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0039_alter_doozeztask_task_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='safe',
            name='job',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='safe.doozezjob'),
        ),
    ]