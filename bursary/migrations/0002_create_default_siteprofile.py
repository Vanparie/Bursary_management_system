from django.db import migrations


def create_default_siteprofile(apps, schema_editor):
    SiteProfile = apps.get_model("bursary", "SiteProfile")
    County = apps.get_model("bursary", "County")
    Constituency = apps.get_model("bursary", "Constituency")

    # Try to attach to an existing constituency first (preferred for your system design)
    constituency = Constituency.objects.first()

    if constituency:
        SiteProfile.objects.create(
            constituency=constituency,
            county=None,
            bursary_type="Constituency",
            branding_name=f"{constituency.name} Bursary System",
            is_active=True,
        )
        return

    # Fallback: if no constituency exists, use county
    county = County.objects.first()

    if county:
        SiteProfile.objects.create(
            county=county,
            constituency=None,
            bursary_type="County",
            branding_name=f"{county.name} Bursary System",
            is_active=True,
        )
        return

    # Final fallback (VERY IMPORTANT for fresh deploys)
    # Create a minimal valid SiteProfile ONLY if both tables are empty
    SiteProfile.objects.create(
        county=None,
        constituency=None,
        bursary_type="Constituency",
        branding_name="Default Bursary System",
        is_active=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("bursary", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_siteprofile),
    ]


