from django.db import models

from .validators import validate_file_extension, validate_file_size

from django.utils import timezone


from django.contrib.auth.models import User

# ✅ County and Constituency should be defined early
class County(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Constituency(models.Model):
    name = models.CharField(max_length=100)
    county = models.ForeignKey(County, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} - {self.county.name}"
    

class Ward(models.Model):
    name = models.CharField(max_length=100)
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='wards')

    def __str__(self):
        return f"{self.name} - {self.constituency.name}"


# 👤 Student applying for the bursary
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=20, unique=True)
    admission_number = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    institution = models.CharField(max_length=100)
    course = models.CharField(max_length=100)
    year_of_study = models.CharField(max_length=50)
    category = models.CharField(max_length=50, choices=[
        ('boarding', 'Boarding'),
        ('day', 'Day'),
        ('college', 'College'),
        ('university', 'University'),
    ])
    has_disability = models.BooleanField(default=False)
    disability_details = models.TextField(blank=True, null=True)
    previous_bursary = models.BooleanField(default=False)
    constituency = models.ForeignKey(Constituency, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.full_name} - {self.admission_number}"

# 👨‍👩‍👧 Family details
class Guardian(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    id_number = models.CharField(max_length=20, blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    income = models.DecimalField(max_digits=10, decimal_places=2)
    phone = models.CharField(max_length=15)

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
        ('fee_structure', 'Fee Structure'),
        ('result_slip', 'Result Slip'),
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
    #constituency_name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='branding/', null=True, blank=True)
    application_deadline = models.DateField(null=True, blank=True)
    constituency = models.ForeignKey(Constituency, on_delete=models.SET_NULL, null=True, blank=True)


    def __str__(self):
        return f"{self.constituency.name if self.constituency else 'No constituency'} - {self.county_name}"
    
    
    def is_application_open(self):
        if self.application_deadline:
            return timezone.now().date() <= self.application_deadline
        return True


class OfficerProfile(models.Model):
    BURSARY_TYPE_CHOICES = [
        ('county', 'County'),
        ('constituency', 'Constituency (NG-CDF)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE)
    bursary_type = models.CharField(max_length=20, choices=BURSARY_TYPE_CHOICES, default='constituency')

    def __str__(self):
        return f"{self.user.username} - {self.constituency.name} ({self.bursary_type})"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True) # Optional

    def __str__(self):
        return f"StudentProfile for {self.user.username}"