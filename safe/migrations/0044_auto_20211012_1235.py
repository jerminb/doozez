# Generated by Django 3.2.4 on 2021-10-12 12:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('safe', '0043_auto_20211012_1124'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gcevent',
            name='details',
        ),
        migrations.RemoveField(
            model_name='gcevent',
            name='links',
        ),
        migrations.AddField(
            model_name='gcevent',
            name='cause',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='gcevent',
            name='description',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='gcevent',
            name='link_id',
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name='gcevent',
            name='gc_created_at',
            field=models.TextField(null=True),
        ),
    ]