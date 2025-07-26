from django.db import models

from .validators import validate_file_extension, validate_file_size

from django.utils import timezone


from django.contrib.auth.models import User


# ✅ County and Constituency should be defined early
class County(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Constituency(models.Model):
    name = models.CharField(max_length=100)
    county = models.ForeignKey(County, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'county')  # Optional: Prevents duplicate constituency names within a county
        ordering = ['county__name', 'name']   # Optional: Orders nicely in admin

    def __str__(self):
        return f"{self.name} - {self.county.name}"

    

class Ward(models.Model):
    name = models.CharField(max_length=100)
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='wards')

    def __str__(self):
        return f"{self.name} - {self.constituency.name}"


def student_profile_pic_path(instance, filename):
    return f'student_photos/{instance.user.username}/{filename}'

# 👤 Student applying for the bursary

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=20, unique=True)
    admission_number = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    institution = models.CharField(max_length=100)  # Renamed from 'school_name' to 'institution' – consistent usage
    course = models.CharField(max_length=100)
    year_of_study = models.CharField(max_length=50)
    must_change_password = models.BooleanField(default=True)  # New field
    date_registered = models.DateTimeField(null=True, blank=True)
    profile_pic = models.ImageField(upload_to=student_profile_pic_path, null=True, blank=True)

    category = models.CharField(max_length=50, choices=[
        ('boarding', 'Boarding'),
        ('day', 'Day'),
        ('college', 'College'),
        ('university', 'University'),
    ])

    has_disability = models.BooleanField(default=False)
    disability_details = models.TextField(blank=True, null=True)
    previous_bursary = models.BooleanField(default=False)
    previous_bursary_details = models.TextField(blank=True, null=True)

    # ✅ Key field for constituency-specific filtering and import validation
    constituency = models.ForeignKey(
        Constituency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )

    def __str__(self):
        return f"{self.full_name} - {self.admission_number}"


# 👨‍👩‍👧 Family details
class Guardian(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    guardian_id_number = models.CharField(max_length=20, blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    income = models.DecimalField(max_digits=10, decimal_places=2)
    guardian_phone = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.name} ({self.relationship})"

# 👧 Other siblings in school
class Sibling(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    school = models.CharField(max_length=100)
    class_level = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} - {self.school}"

# 📤 Application itself
class BursaryApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    BURSARY_TYPE_CHOICES = [
        ('county', 'County Bursary'),
        ('constituency', 'NG-CDF Constituency Bursary'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    
    # Constituency is auto-assigned and not editable
    constituency = models.ForeignKey(Constituency, on_delete=models.PROTECT)
    
    # Ward chosen by student, can be null initially
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True)
    
    fees_required = models.DecimalField(max_digits=10, decimal_places=2)
    fees_paid = models.DecimalField(max_digits=10, decimal_places=2)
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    amount_awarded = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    supporting_doc = models.FileField(upload_to='uploads/', null=True, blank=True)

    date_applied = models.DateTimeField(auto_now_add=True)

    bursary_type = models.CharField(max_length=20, choices=BURSARY_TYPE_CHOICES, default='constituency')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.student} - {self.bursary_type} - {self.status}"


    # ✅ NEW FIELD
    bursary_type = models.CharField(max_length=20, choices=BURSARY_TYPE_CHOICES, default='constituency')

    def __str__(self):
        return f"{self.student.full_name} - {self.bursary_type.title()} - {self.status}"


def user_directory_path(instance, filename):
    return f'documents/{instance.application.student.admission_number}/{filename}'


# 📎 Uploaded documents (fee structure, ID, birth cert, result slips, etc.)
class SupportingDocument(models.Model):
    DOCUMENT_TYPES = [
        ('birth_cert', 'Birth Certificate'),
        ('id_copy', 'ID Copy'),
        ('admission_letter', 'Admission Letter'),
        ('fee_structure', 'Fee Structure'),
        ('result_slip', 'KCPE/KCSE/Result Slip'),
        ('death_cert', 'Death Certificate'),
        ('disability_cert', 'Disability Certificate'),
        ('other', 'Other'),
    ]

    application = models.ForeignKey(BursaryApplication, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(
        upload_to=user_directory_path,
        validators=[validate_file_extension, validate_file_size]
    )
    

    def __str__(self):
        return f"{self.document_type} - {self.file.name}"


class SiteProfile(models.Model):
    county_name = models.CharField(max_length=100)

    # Supports unique branding and application deadlines per constituency
    constituency = models.ForeignKey(
        Constituency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_profiles'
    )

    logo = models.ImageField(upload_to='branding/', null=True, blank=True)
    application_deadline = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.constituency.name if self.constituency else 'No constituency'} - {self.county_name}"

    def is_application_open(self):
        """
        Determines if the application window is still open based on the deadline.
        """
        if self.application_deadline:
            return timezone.now().date() <= self.application_deadline
        return True


class OfficerProfile(models.Model):
    BURSARY_TYPE_CHOICES = [
        ('county', 'County'),
        ('constituency', 'Constituency (NG-CDF)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    constituency = models.ForeignKey('Constituency', on_delete=models.CASCADE)
    bursary_type = models.CharField(max_length=20, choices=BURSARY_TYPE_CHOICES, default='constituency')

    # ✅ NEW FIELDS
    is_active = models.BooleanField(default=True)
    is_manager = models.BooleanField(default=False)  # Only managers can manage other officers
    profile_pic = models.ImageField(upload_to='officer_profiles/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, help_text="Officer's phone number (optional)")
    designation = models.CharField(max_length=50, blank=True, help_text="Position e.g. 'Clerk', 'Chairperson', etc.")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.constituency.name} [{self.get_bursary_type_display()}]"


class OfficerActivityLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('add_officer', 'Added Officer'),
        ('edit_officer', 'Edited Officer'),
        ('delete_officer', 'Deleted Officer'),
        ('review_application', 'Reviewed Application'),
        ('change_status', 'Changed Application Status'),
    ]

    officer = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.officer.username} - {self.get_action_display()} at {self.timestamp:%Y-%m-%d %H:%M}"



class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True) # Optional

    def __str__(self):
        return f"StudentProfile for {self.user.username}"