from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from .validators import validate_file_extension, validate_file_size
import os
from django.core.exceptions import ValidationError


# ========================
# Location Models
# ========================
class County(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Constituency(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name="constituencies")

    class Meta:
        unique_together = ("name", "county")
        ordering = ["county__name", "name"]

    def __str__(self):
        return f"{self.name} - {self.county.name}"


class Ward(models.Model):
    name = models.CharField(max_length=100)
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name="wards")

    def __str__(self):
        return f"{self.name} - {self.constituency.name}"


# ========================
# Student Model
# ========================
def student_profile_pic_path(instance, filename):
    return f"student_photos/{instance.user.username}/{filename}"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    first_name = models.CharField(max_length=100, db_index=True)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, db_index=True)

    # Identity
    id_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    admission_number = models.CharField(max_length=20, unique=True, db_index=True)
    nemis_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)

    # Academic
    institution = models.CharField(max_length=100)
    course = models.CharField(max_length=100, blank=True, null=True)
    year_of_study = models.CharField(max_length=50, blank=True, null=True)

    category = models.CharField(
        max_length=50,
        choices=[
            ("boarding", "Boarding"),
            ("day", "Day"),
            ("college", "College"),
            ("university", "University"),
        ],
        db_index=True,
    )

    # Extra info
    has_disability = models.BooleanField(default=False)
    disability_details = models.TextField(blank=True, null=True)
    previous_bursary = models.BooleanField(default=False)
    previous_bursary_details = models.TextField(blank=True, null=True)

    # Registration
    date_registered = models.DateTimeField(null=True, blank=True, default=timezone.now)
    profile_pic = models.ImageField(upload_to=student_profile_pic_path, null=True, blank=True)

    # Location (auto-filled from SiteProfile at signup)
    county = models.ForeignKey(
        County, on_delete=models.SET_NULL, null=True, blank=True, related_name="students"
    )
    constituency = models.ForeignKey(
        Constituency, on_delete=models.SET_NULL, null=True, blank=True, related_name="students"
    )

    class Meta:
        ordering = ["first_name", "last_name", "admission_number"]

    def __str__(self):
        return f"{self.full_name} - {self.admission_number}"

    @property
    def full_name(self):
        """Builds full name dynamically (ignores missing middle name)."""
        names = [self.first_name, self.middle_name, self.last_name]
        return " ".join([n for n in names if n]).strip()

    def clean(self):
        """Ensure empty strings are stored as NULL for unique fields."""
        if self.id_number == "":
            self.id_number = None
        if self.nemis_number == "":
            self.nemis_number = None

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# ========================
# Family Models
# ========================
class Guardian(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="guardians")
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    guardian_id_number = models.CharField(max_length=20, blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    income = models.DecimalField(max_digits=10, decimal_places=2)
    guardian_phone = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.name} ({self.relationship})"


class Sibling(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="siblings")
    name = models.CharField(max_length=100)
    school = models.CharField(max_length=100)
    class_level = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} - {self.school}"


# ========================
# Bursary Application
# ========================
class ApplicationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class BursaryType(models.TextChoices):
    COUNTY = "county", "County Bursary"
    CONSTITUENCY = "constituency", "NG-CDF Constituency Bursary"


class BursaryApplication(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="applications")
    constituency = models.ForeignKey(Constituency, on_delete=models.PROTECT)
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True)

    fees_required = models.DecimalField(max_digits=10, decimal_places=2)
    fees_paid = models.DecimalField(max_digits=10, decimal_places=2)
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    amount_awarded = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    supporting_doc = models.FileField(upload_to="uploads/", null=True, blank=True)
    date_applied = models.DateTimeField(auto_now_add=True, db_index=True)

    bursary_type = models.CharField(
        max_length=20, choices=BursaryType.choices, default=BursaryType.CONSTITUENCY, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.PENDING, db_index=True
    )
    feedback = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-date_applied"]

    def __str__(self):
        return f"{self.student.full_name} - {self.get_bursary_type_display()} - {self.get_status_display()}"


# ========================
# Supporting Documents
# ========================
def user_directory_path(instance, filename):
    return f"documents/{instance.application.student.admission_number}/{filename}"


class SupportingDocument(models.Model):
    class DocumentType(models.TextChoices):
        BIRTH_CERT = "birth_cert", "Birth Certificate"
        ID_COPY = "id_copy", "ID Copy"
        ADMISSION_LETTER = "admission_letter", "Admission Letter"
        FEE_STRUCTURE = "fee_structure", "Fee Structure"
        RESULT_SLIP = "result_slip", "KCPE/KCSE/Result Slip"
        DEATH_CERT = "death_cert", "Death Certificate"
        DISABILITY_CERT = "disability_cert", "Disability Certificate"
        OTHER = "other", "Other"

    application = models.ForeignKey(
        BursaryApplication, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=50, choices=DocumentType.choices, db_index=True)
    file = models.FileField(
        upload_to=user_directory_path,
        validators=[validate_file_extension, validate_file_size],
    )

    def __str__(self):
        return f"{self.get_document_type_display()} - {os.path.basename(self.file.name)}"


# ========================
# Site Profile (Branding & Scope)
# ========================
class SiteProfile(models.Model):
    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True, blank=True)
    constituency = models.ForeignKey(
        Constituency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="site_profiles",
    )
    bursary_type = models.CharField(
        max_length=50,
        choices=[("County", "County"), ("Constituency", "Constituency")],
        default="Constituency",
    )

    # Branding
    branding_name = models.CharField(max_length=255, default="BursaryFlow")
    branding_logo = models.ImageField(upload_to="branding/", null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True, db_index=True)

    # Application window
    application_deadline = models.DateField(null=True, blank=True)

    def __str__(self):
        if self.constituency:
            return f"{self.constituency.name} Constituency"
        elif self.county:
            return f"{self.county.name} County"
        return "Unassigned Site Profile"

    def clean(self):
        """Ensure SiteProfile is tied to either county OR constituency, not both."""
        if self.county and self.constituency:
            raise ValidationError("A SiteProfile cannot be linked to both a county and a constituency.")
        if not self.county and not self.constituency:
            raise ValidationError("A SiteProfile must be linked to either a county or a constituency.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def is_application_open(self):
        return not self.application_deadline or timezone.now().date() <= self.application_deadline

    @property
    def level(self):
        """Returns 'county' or 'constituency' depending on which is set."""
        if self.county:
            return "county"
        if self.constituency:
            return "constituency"
        return None

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()


# ========================
# Officer Models
# ========================
class OfficerProfile(models.Model):
    class BursaryType(models.TextChoices):
        COUNTY = "county", "County"
        CONSTITUENCY = "constituency", "Constituency (NG-CDF)"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="officer_profile")
    constituency = models.ForeignKey(
        Constituency,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Leave blank if officer is county-level",
    )
    bursary_type = models.CharField(
        max_length=20, choices=BursaryType.choices, default=BursaryType.CONSTITUENCY, db_index=True
    )

    is_active = models.BooleanField(default=True, db_index=True)
    is_manager = models.BooleanField(default=False)
    profile_pic = models.ImageField(upload_to="officer_profiles/", blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, help_text="Officer's phone number (optional)")
    designation = models.CharField(max_length=50, blank=True, help_text="Position e.g. 'Clerk', 'Chairperson', etc.")

    def __str__(self):
        constituency_name = self.constituency.name if self.constituency else "County"
        return f"{self.user.get_full_name() or self.user.username} - {constituency_name} [{self.get_bursary_type_display()}]"


class OfficerActivityLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = "login", "Login"
        ADD_OFFICER = "add_officer", "Added Officer"
        EDIT_OFFICER = "edit_officer", "Edited Officer"
        DELETE_OFFICER = "delete_officer", "Deleted Officer"
        REVIEW_APPLICATION = "review_application", "Reviewed Application"
        CHANGE_STATUS = "change_status", "Changed Application Status"
        RESOLVE_SUPPORT = "resolve_support_request", "Resolved Support Request"

    officer = models.ForeignKey(OfficerProfile, on_delete=models.CASCADE, related_name="logs")
    action = models.CharField(max_length=50, choices=Action.choices, db_index=True)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.officer} - {self.get_action_display()} at {self.timestamp:%Y-%m-%d %H:%M}"


# ========================
# Support Request
# ========================
class SupportRequest(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="support_requests")
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved = models.BooleanField(default=False, db_index=True)
    officer_action = models.TextField(blank=True, null=True)
    viewed_by_student = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.user.username} - {self.subject}"

    @property
    def feedback(self):
        return self.officer_action




