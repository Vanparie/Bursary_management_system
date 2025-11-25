from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Student, SiteProfile, Constituency


class StudentResource(resources.ModelResource):
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'username')
    )
    constituency = fields.Field(
        column_name='constituency',
        attribute='constituency',
        widget=ForeignKeyWidget(Constituency, 'name')
    )

    def before_import_row(self, row, **kwargs):
        # ✅ Enforce constituency restriction
        site_profile = SiteProfile.objects.first()
        allowed_constituency = site_profile.constituency.name if site_profile and site_profile.constituency else None
        row_constituency = row.get('constituency', '').strip()

        if allowed_constituency and row_constituency != allowed_constituency:
            raise Exception(
                f"Row rejected: '{row.get('full_name')}' does not belong to constituency '{allowed_constituency}'. Found '{row_constituency}' instead."
            )

        # ✅ Auto-create user if not exists
        admission_number = row.get('admission_number')
        email = row.get('email', f"{admission_number}@studentsystem.com")

        if not User.objects.filter(username=admission_number).exists():
            password = get_random_string(length=8)
            User.objects.create_user(
                username=admission_number,
                email=email,
                password=admission_number  # Set admission number as initial password
            )

    def get_instance(self, instance_loader, row):
        # Prevent duplicates by matching admission_number
        return self._meta.model.objects.filter(admission_number=row['admission_number']).first()

    def before_save_instance(self, instance, row, **kwargs):
    # ✅ Assign user to student record
        instance.user = User.objects.get(username=instance.admission_number)


    class Meta:
        model = Student
        import_id_fields = ['admission_number']
        fields = (
            'user',
            'admission_number',
            'id_number',
            'full_name',
            'constituency',
            'institution',
            'year_of_study',
            'phone',
            'email',
        )
