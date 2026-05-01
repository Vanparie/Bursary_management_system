from django.db import migrations
from django.utils.text import slugify

def create_siteprofile(apps, schema_editor):
    County = apps.get_model("bursary", "County")
    Constituency = apps.get_model("bursary", "Constituency")
    SiteProfile = apps.get_model("bursary", "SiteProfile")

    county, _ = County.objects.get_or_create(name="Samburu")

    constituency, _ = Constituency.objects.get_or_create(
        name="Samburu West",
        county=county
    )

    SiteProfile.objects.get_or_create(
        county=county,
        constituency=constituency,
        bursary_type="Constituency",
        defaults={
            "branding_name": "Samburu West Constituency",
            "is_active": True,
            "slug": slugify("samburu-west"),
        }
    )

class Migration(migrations.Migration):

    dependencies = [
        ("bursary", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_siteprofile),
    ]
