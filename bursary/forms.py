from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import (
    Student, BursaryApplication, SupportingDocument,
    Guardian, Sibling, Ward, OfficerProfile, SiteProfile
)
from .utils.mock_verification import verify_id, verify_nemis


# ========================
# Student Form (Admin Use)
# ========================
class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'middle_name', 'last_name', 'id_number', 'nemis_number',
            'admission_number', 'institution', 'course', 'year_of_study', 'category',
            'phone', 'email',
            'has_disability',
            'disability_details',
            'previous_bursary',
            'previous_bursary_details',
        ]
        widgets = {
            'has_disability': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'previous_bursary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'disability_details': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'previous_bursary_details': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 0712345678'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        readonly_fields = [
            'first_name', 'middle_name', 'last_name', 'id_number', 'nemis_number',
            'admission_number',
        ]
        for field_name in readonly_fields:
            self.fields[field_name].disabled = True

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip().replace(" ", "")
        if not phone.isdigit() or len(phone) != 10 or not (phone.startswith("07") or phone.startswith("01")):
            raise forms.ValidationError("Enter a valid Kenyan phone number (10 digits, starting with 07 or 01).")
        return phone


# ========================
# Student Login Form
# ========================
class StudentLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="National ID / NEMIS Number",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your National ID or NEMIS Number'
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)


# ========================
# Student Profile Form
# ========================
class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'middle_name', 'last_name', 'id_number', 'nemis_number', 'admission_number',
            'institution', 'course', 'year_of_study', 'category',
            'profile_pic', 'phone', 'email'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 0712345678'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['first_name', 'middle_name', 'last_name', 'id_number', 'nemis_number', 'admission_number']:
            if field_name in self.fields:
                self.fields[field_name].disabled = True

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip().replace(" ", "")
        if not phone.isdigit() or len(phone) != 10 or not (phone.startswith("07") or phone.startswith("01")):
            raise forms.ValidationError("Enter a valid Kenyan phone number (10 digits, starting with 07 or 01).")
        return phone


# ========================
# Guardian Form
# ========================
class GuardianForm(forms.ModelForm):
    class Meta:
        model = Guardian
        fields = ['name', 'relationship', 'guardian_id_number', 'occupation', 'income', 'guardian_phone']


# ========================
# Sibling Form
# ========================
class SiblingForm(forms.ModelForm):
    class Meta:
        model = Sibling
        fields = ['name', 'school', 'class_level']


# ========================
# Bursary Application Form
# ========================
class BursaryApplicationForm(forms.ModelForm):
    class Meta:
        model = BursaryApplication
        fields = ['constituency', 'ward', 'fees_required', 'fees_paid', 'amount_requested']

    def __init__(self, *args, **kwargs):
        student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        if student:
            if not self.initial.get('constituency') and hasattr(student, 'constituency'):
                self.fields['constituency'].initial = student.constituency
            self.fields['constituency'].disabled = True
            if student.constituency:
                self.fields['ward'].queryset = Ward.objects.filter(constituency=student.constituency)
            else:
                self.fields['ward'].queryset = Ward.objects.none()

    def clean_constituency(self):
        constituency = self.cleaned_data.get('constituency')
        if not constituency:
            raise forms.ValidationError('Please select a valid constituency.')
        return constituency


# ========================
# Supporting Document Form
# ========================
class SupportingDocumentForm(forms.ModelForm):
    class Meta:
        model = SupportingDocument
        fields = ['document_type', 'file']


# ========================
# Verified Student Signup Form
# ========================

import uuid

IDENTIFICATION_CHOICES = [
    ("id", "National ID"),
    ("nemis", "NEMIS"),
]

class VerifiedStudentSignupForm(forms.ModelForm):
    first_name = forms.CharField(required=True)
    middle_name = forms.CharField(required=False)
    last_name = forms.CharField(required=True)
    admission_number = forms.CharField(required=True, help_text="Your institution admission number")
    email = forms.EmailField(required=True)

    id_type = forms.ChoiceField(
        choices=IDENTIFICATION_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        label="Choose your Identification",
    )

    id_number = forms.CharField(required=False, label="National ID")
    nemis_number = forms.CharField(required=False, label="NEMIS Number")
    guardian_id_number = forms.CharField(required=False, label="Guardian National ID")

    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Password confirmation")

    # ✅ New field: Must agree to terms
    agree_to_terms = forms.BooleanField(
        label="I agree to the Terms of Use and Privacy Policy",
        required=True,
        error_messages={
            "required": "You must agree to the Terms of Use and Privacy Policy to register."
        }
    )

    class Meta:
        model = Student
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "admission_number",
            "email",
        ]

    # ----------------------
    # Field-level validation
    # ----------------------
    def clean_id_number(self):
        id_number = self.cleaned_data.get("id_number")
        if id_number and Student.objects.filter(id_number=id_number).exists():
            raise ValidationError("This National ID is already registered.")
        return id_number

    def clean_nemis_number(self):
        nemis_number = self.cleaned_data.get("nemis_number")
        if nemis_number and Student.objects.filter(nemis_number=nemis_number).exists():
            raise ValidationError("This NEMIS Number is already registered.")
        return nemis_number

    def clean(self):
        cleaned_data = super().clean()
        id_type = cleaned_data.get("id_type")
        id_number = cleaned_data.get("id_number")
        nemis_number = cleaned_data.get("nemis_number")
        guardian_id_number = cleaned_data.get("guardian_id_number")

        # Ensure password match
        pw1, pw2 = cleaned_data.get("password1"), cleaned_data.get("password2")
        if pw1 and pw2 and pw1 != pw2:
            raise ValidationError("Passwords do not match.")

        # Ensure agree_to_terms is checked
        if not cleaned_data.get("agree_to_terms"):
            raise ValidationError("You must agree to the Terms of Use and Privacy Policy to register.")

        # Get site context
        site = SiteProfile.objects.filter(is_active=True).first()
        county = getattr(site, "county", None)
        constituency = getattr(site, "constituency", None)

        county_name = county.name if county else None
        constituency_name = constituency.name if constituency else None

        # Verification logic
        if id_type == "id":
            if not id_number:
                raise ValidationError("National ID is required.")
            is_valid, message, _, _ = verify_id(
                id_number,
                county_name=county_name,
                constituency_name=constituency_name,
            )
        elif id_type == "nemis":
            if not nemis_number:
                raise ValidationError("NEMIS number is required.")
            is_valid, message, _, _ = verify_nemis(
                nemis_number,
                county_name=county_name,
                constituency_name=constituency_name,
                guardian_id=guardian_id_number,
            )
        else:
            raise ValidationError("Invalid identification type.")

        if not is_valid:
            raise ValidationError(message)

        return cleaned_data

    def save(self, commit=True):
        cleaned_data = self.cleaned_data

        # prefer the identity used at signup as username
        base_username = None
        if cleaned_data.get("id_type") == "id":
            base_username = (cleaned_data.get("id_number") or "").strip()
        elif cleaned_data.get("id_type") == "nemis":
            base_username = (cleaned_data.get("nemis_number") or "").strip()

        # final fallback
        if not base_username:
            base_username = cleaned_data.get("admission_number") or f"student_{uuid.uuid4().hex[:8]}"

        # sanitize minimally (remove spaces)
        base_username = base_username.replace(" ", "")

        # ensure unique username in User table
        username = base_username
        counter = 0
        while User.objects.filter(username=username).exists():
            counter += 1
            username = f"{base_username}_{counter}"

        # Create the Django user
        user = User.objects.create_user(
            username=username,
            first_name=cleaned_data["first_name"],
            last_name=cleaned_data["last_name"],
            email=cleaned_data["email"],
            password=cleaned_data["password1"],
        )

        # Create Student profile
        student = Student.objects.create(
            user=user,
            first_name=cleaned_data["first_name"],
            middle_name=cleaned_data.get("middle_name", ""),
            last_name=cleaned_data["last_name"],
            admission_number=cleaned_data["admission_number"],
            email=cleaned_data["email"],
            id_number=cleaned_data["id_number"] if cleaned_data["id_type"] == "id" else None,
            nemis_number=cleaned_data["nemis_number"] if cleaned_data["id_type"] == "nemis" else None,
        )

        if commit:
            user.save()
            student.save()

        return student



# ========================
# User Form
# ========================
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']


# ========================
# Officer Forms
# ========================
class OfficerUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Officer ID Number'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        help_texts = {f: "" for f in fields}

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username.isdigit() or len(username) != 8:
            raise forms.ValidationError("Use a valid Kenyan ID number (8 digits).")
        return username

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            self.add_error("email", "This email address is already in use.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class OfficerProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = OfficerProfile
        fields = ['phone', 'profile_pic', 'designation']
        widgets = {
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_pic': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['email'].initial = user.email

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        if email and User.objects.filter(email=email).exclude(pk=getattr(self.instance.user, "pk", None)).exists():
            self.add_error("email", "This email address is already in use.")
        return cleaned_data

    def save(self, commit=True):
        officer = super().save(commit=False)
        email = self.cleaned_data.get('email')
        if email and hasattr(officer, 'user'):
            officer.user.email = email
            officer.user.save()
        if commit:
            officer.save()
        return officer


class OfficerSelfProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = OfficerProfile
        fields = ['phone', 'profile_pic']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_pic': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['email'].initial = user.email

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        if email and User.objects.filter(email=email).exclude(pk=getattr(self.instance.user, "pk", None)).exists():
            self.add_error("email", "This email address is already in use.")
        return cleaned_data

    def save(self, commit=True):
        officer = super().save(commit=False)
        email = self.cleaned_data.get('email')
        if email and hasattr(officer, 'user'):
            officer.user.email = email
            officer.user.save()
        if commit:
            officer.save()
        return officer


# ========================
# Upgrade to ID Form
# ========================
class UpgradeToIDForm(forms.Form):
    id_number = forms.CharField(max_length=20)

    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop("student", None)
        super().__init__(*args, **kwargs)

    def clean_id_number(self):
        id_number = self.cleaned_data["id_number"]
        valid, message, _, _ = verify_id(id_number)
        if not valid:
            raise ValidationError("This ID could not be verified.")
        if Student.objects.filter(id_number=id_number).exclude(pk=self.student.pk).exists():
            raise ValidationError("This ID is already linked to another account.")
        return id_number


# ========================
# Password Change Form
# ========================
class SimplePasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = None
            field.widget.attrs.update({'class': 'form-control'})



from .models import SupportRequest

class SupportRequestForm(forms.ModelForm):
    class Meta:
        model = SupportRequest
        fields = ['subject', 'message']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief summary of your issue'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe your issue in detail'}),
        }

