from django.db import migrations


def setup_default_site(apps, schema_editor):
    """
    Set up or rename the default example.com site created by Django.
    """
    try:
        Site = apps.get_model("sites", "Site")
    except:
        return

    name = "Doozez.co.uk"
    domain = "doozez.co.uk"

    try:
        site = Site.objects.get(domain="example.com")
        site.name = name
        site.domain = domain
        site.save()

    except Site.DoesNotExist:
        # No site with domain example.com exists.
        # Create a default site, but only if no sites exist.
        if Site.objects.count() == 0:
            Site.objects.create(name=name, domain=domain)


class Migration(migrations.Migration):

    dependencies = [
        ("safe", "0001_initial"),
        ('safe', '0040_safe_job'),
    ]

    operations = [
        migrations.RunPython(setup_default_site, migrations.RunPython.noop),
    ]