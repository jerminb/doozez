from django.contrib.auth import get_user_model
from django.db import migrations

from .. import utils


def forwards_func(apps, schema_editor):
    User = apps.get_model("safe", "DoozezUser")
    db_alias = schema_editor.connection.alias
    User.objects.using(db_alias).create(email='system@doozez.internal', password=utils.id_generator(), is_system=True)


def reverse_func(apps, schema_editor):
    User = apps.get_model("safe", "DoozezUser")
    db_alias = schema_editor.connection.alias
    User.objects.using(db_alias).filter(email='system@doozez.internal').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('safe', '0026_doozezuser_is_system'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
