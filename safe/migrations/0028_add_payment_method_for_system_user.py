from django.db import migrations

from .. import utils


def forwards_func(apps, schema_editor):
    User = apps.get_model("safe", "DoozezUser")
    PaymentMethod = apps.get_model("safe", "PaymentMethod")
    db_alias = schema_editor.connection.alias
    system_user = User.objects.using(db_alias).filter(is_system=True).first()
    PaymentMethod.objects.using(db_alias).create(user=system_user, is_default=True)


def reverse_func(apps, schema_editor):
    User = apps.get_model("safe", "DoozezUser")
    PaymentMethod = apps.get_model("safe", "PaymentMethod")
    db_alias = schema_editor.connection.alias
    system_user = User.objects.using(db_alias).filter(is_system=True).first()
    PaymentMethod.objects.using(db_alias).filter(user=system_user, is_default=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('safe', '0027_add_system_user'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]