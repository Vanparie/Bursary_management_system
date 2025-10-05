from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bursary', '0002_siteprofile_bursary_type'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward migration: add unique constraint
            sql="ALTER TABLE auth_user ADD CONSTRAINT unique_email UNIQUE (email);",
            # Backward migration: drop unique constraint
            reverse_sql="ALTER TABLE auth_user DROP CONSTRAINT unique_email;",
        ),
    ]




