from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import (
    Student, BursaryApplication, SupportingDocument,
    Guardian, Sibling, Ward, OfficerProfile, SiteProfile, SupportRequest
)
from .utils.mock_verification import verify_id
import uuid


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
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from .models import Student

User = get_user_model()


class StudentLoginForm(forms.Form):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_cache = None

    def clean(self):
        cleaned_data = super().clean()
        identifier = (cleaned_data.get('username') or "").strip()
        password = cleaned_data.get('password')

        # If one of the fields is missing, let the field validators handle it.
        if not identifier or not password:
            return cleaned_data

        # 1) Try to authenticate directly (identifier might already be the User.username)
        user = authenticate(username=identifier, password=password)
        if user:
            self.user_cache = user
            return cleaned_data

        # 2) Try to find a Student matching ID / NEMIS / admission_number
        student_qs = Student.objects.filter(
            Q(id_number=identifier) | Q(nemis_number=identifier) | Q(admission_number=identifier)
        )
        if student_qs.exists():
            student = student_qs.first()
            # attempt authentication using the linked user's username (safe)
            user = authenticate(username=student.user.username, password=password)
            if user:
                self.user_cache = user
                return cleaned_data
            # student found -> wrong password
            self.add_error('password', 'Incorrect password. Please try again.')
            return cleaned_data

        # 3) If there is a User with this username but auth failed -> wrong password
        if User.objects.filter(username=identifier).exists():
            self.add_error('password', 'Incorrect password. Please try again.')
        else:
            # no account found for this identifier
            self.add_error('username', 'No account found for this National ID or NEMIS Number.')

        return cleaned_data

    def get_user(self):
        return self.user_cache


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
# bursary/forms.py (partial)

class GuardianForm(forms.ModelForm):
    class Meta:
        model = Guardian
        fields = ['name', 'relationship', 'guardian_id_number', 'occupation', 'income', 'guardian_phone']

    def __init__(self, *args, **kwargs):
        student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        self.student = student

        # ✅ If student used NEMIS as identification
        if student and student.nemis_number:
            # Try to fetch existing guardian record
            guardian = Guardian.objects.filter(student=student).first()

            if guardian:
                # Prefill from guardian record
                self.fields['name'].initial = guardian.name
                self.fields['guardian_id_number'].initial = guardian.guardian_id_number
            else:
                # Try to prefill from mock verification (if applicable)
                try:
                    from bursary.utils.mock_verification import verify_nemis_details
                    data = verify_nemis_details(student.nemis_number)
                    if data:
                        self.fields['name'].initial = data.get('guardian_name', '')
                        self.fields['guardian_id_number'].initial = data.get('guardian_id_number', '')
                except Exception:
                    pass

            # ✅ Make them uneditable
            self.fields['name'].disabled = True
            self.fields['guardian_id_number'].disabled = True

            # Add a visual cue (greyed-out style)
            self.fields['name'].widget.attrs.update({
                'class': 'form-control locked-field',
                'readonly': True
            })
            self.fields['guardian_id_number'].widget.attrs.update({
                'class': 'form-control locked-field',
                'readonly': True
            })

    def clean(self):
        """Ensure locked fields are preserved correctly."""
        cleaned_data = super().clean()
        student = getattr(self, 'student', None)

        if student and student.nemis_number:
            guardian = Guardian.objects.filter(student=student).first()
            if guardian:
                cleaned_data['name'] = guardian.name
                cleaned_data['guardian_id_number'] = guardian.guardian_id_number
            else:
                try:
                    from bursary.utils.mock_verification import verify_nemis_details
                    data = verify_nemis_details(student.nemis_number)
                    if data:
                        cleaned_data['name'] = data.get('guardian_name', '')
                        cleaned_data['guardian_id_number'] = data.get('guardian_id_number', '')
                except Exception:
                    pass
        return cleaned_data

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

IDENTIFICATION_CHOICES = [
    ("id", "National ID"),
    ("nemis", "NEMIS"),
]


class VerifiedStudentSignupForm(forms.ModelForm):
    """
    Updated signup form that:
    - Supports guardian first/last names for NEMIS verification.
    - Reads frontend hidden flags (id_verified_flag / guardian_verified_flag)
      and trusts them to avoid redundant re-checks.
    - Falls back to server-side verify_id(...) if the flag is absent/false.
    - Attaches validation errors to fields (so template displays them inline).
    """

    first_name = forms.CharField(required=True)
    middle_name = forms.CharField(required=False)
    last_name = forms.CharField(required=True)
    admission_number = forms.CharField(
        required=True, help_text="Your institution admission number"
    )
    email = forms.EmailField(required=True)

    id_type = forms.ChoiceField(
        choices=IDENTIFICATION_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        label="Choose your Identification",
    )

    # --- Identification Fields ---
    id_number = forms.CharField(required=False, label="National ID")
    nemis_number = forms.CharField(required=False, label="NEMIS Number")
    guardian_id_number = forms.CharField(required=False, label="Guardian National ID")
    guardian_first_name = forms.CharField(required=False, label="Guardian First Name")
    guardian_last_name = forms.CharField(required=False, label="Guardian Last Name")

    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Password confirmation")

    agree_to_terms = forms.BooleanField(
        label="I agree to the Terms of Use and Privacy Policy",
        required=True,
        error_messages={
            "required": "You must agree to the Terms of Use and Privacy Policy to register."
        },
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
        id_number = (self.cleaned_data.get("id_number") or "").strip()
        if id_number and Student.objects.filter(id_number=id_number).exists():
            raise ValidationError("This National ID is already registered.")
        return id_number

    def clean_nemis_number(self):
        nemis_number = self.cleaned_data.get("nemis_number")
        if nemis_number and Student.objects.filter(nemis_number=nemis_number).exists():
            raise ValidationError("This NEMIS Number is already registered.")
        return nemis_number

    # ----------------------
    # Full form validation
    # ----------------------
    def clean(self):
        cleaned_data = super().clean()
        id_type = cleaned_data.get("id_type")
        id_number = cleaned_data.get("id_number")
        nemis_number = cleaned_data.get("nemis_number")
        guardian_id_number = cleaned_data.get("guardian_id_number")
        guardian_first_name = cleaned_data.get("guardian_first_name")
        guardian_last_name = cleaned_data.get("guardian_last_name")

        # Ensure passwords match
        pw1, pw2 = cleaned_data.get("password1"), cleaned_data.get("password2")
        if pw1 and pw2 and pw1 != pw2:
            self.add_error("password2", "Passwords do not match.")

        # Ensure terms checkbox
        if not cleaned_data.get("agree_to_terms"):
            self.add_error(
                "agree_to_terms",
                "You must agree to the Terms of Use and Privacy Policy to register.",
            )

        # Site context
        site = SiteProfile.get_active()
        county_name = getattr(site, "county", None)
        constituency_name = getattr(site, "constituency", None)
        county_name = county_name.name if county_name else None
        constituency_name = constituency_name.name if constituency_name else None

        # Hidden frontend verification flags
        raw = self.data or {}
        id_verified_flag = str(raw.get("id_verified_flag", "")).lower() == "true"
        guardian_verified_flag = str(raw.get("guardian_verified_flag", "")).lower() == "true"

        is_valid = False
        message = None

        # --- National ID Verification ---
        if id_type == "id":
            if not id_number:
                self.add_error("id_number", "National ID is required.")
                return cleaned_data

            if id_verified_flag:
                is_valid = True
            else:
                try:
                    # verify_id returns (is_valid, message, verified_county, verified_constituency, verified_name)
                    is_valid, message, _, _, verified_name = verify_id(
                        id_number=id_number,
                        county_name=county_name,
                        constituency_name=constituency_name,
                    )
                    if not is_valid:
                        self.add_error("id_number", message)
                except Exception:
                    self.add_error("id_number", "⚠️ Network error during verification.")

        # --- NEMIS + Guardian Verification ---
        elif id_type == "nemis":
            if not nemis_number:
                self.add_error("nemis_number", "NEMIS number is required.")
            if not guardian_id_number:
                self.add_error(
                    "guardian_id_number",
                    "Guardian National ID is required for NEMIS verification.",
                )
                return cleaned_data
            if not guardian_first_name or not guardian_last_name:
                self.add_error(None, "Guardian first and last name are required for NEMIS verification.")
                return cleaned_data

            if guardian_verified_flag:
                is_valid = True
            else:
                try:
                    is_valid, message, _, _, verified_name = verify_id(
                        id_number=guardian_id_number,
                        first_name=guardian_first_name,
                        last_name=guardian_last_name,
                        county_name=county_name,
                        constituency_name=constituency_name,
                    )
                    if not is_valid:
                        self.add_error("guardian_id_number", message)
                    else:
                        # store the verified guardian name for save()
                        self._verified_guardian_name = verified_name
                except Exception:
                    self.add_error(
                        "guardian_id_number",
                        "⚠️ Network error during verification. Please try again.",
                    )

        else:
            self.add_error("id_type", "Invalid identification type selected.")

        # Final fallback
        if not is_valid and not self.errors:
            self.add_error(None, message or "Verification failed. Please check your details and try again.")

        return cleaned_data

    # ----------------------
    # Save user and student
    # ----------------------
    def save(self, commit=True):
        cleaned_data = self.cleaned_data

        # Username logic
        base_username = None
        if cleaned_data.get("id_type") == "id":
            base_username = (cleaned_data.get("id_number") or "").strip()
        elif cleaned_data.get("id_type") == "nemis":
            base_username = (cleaned_data.get("nemis_number") or "").strip()

        if not base_username:
            base_username = (
                cleaned_data.get("admission_number")
                or f"student_{uuid.uuid4().hex[:8]}"
            )

        base_username = base_username.replace(" ", "")
        username = base_username
        counter = 0
        while User.objects.filter(username=username).exists():
            counter += 1
            username = f"{base_username}_{counter}"

        # Create Django user
        user = User.objects.create_user(
            username=username,
            first_name=cleaned_data["first_name"],
            last_name=cleaned_data["last_name"],
            email=cleaned_data["email"],
            password=cleaned_data["password1"],
        )

        # ---------------------------
        # Ensure Student profile exists and is linked
        # ---------------------------
        student, created = Student.objects.get_or_create(
            user=user,
            defaults={
                "first_name": cleaned_data["first_name"],
                "middle_name": cleaned_data.get("middle_name", ""),
                "last_name": cleaned_data["last_name"],
                "admission_number": cleaned_data["admission_number"],
                "email": cleaned_data["email"],
                "id_number": cleaned_data["id_number"]
                if cleaned_data["id_type"] == "id"
                else None,
                "nemis_number": cleaned_data["nemis_number"]
                if cleaned_data["id_type"] == "nemis"
                else None,
            },
        )

        if commit:
            user.save()
            student.save()

        # ---------------------------
        # Ensure Guardian exists for NEMIS signups
        # ---------------------------
        try:
            if cleaned_data.get("id_type") == "nemis":
                guardian_id = cleaned_data.get("guardian_id_number") or ""
                guardian_first = cleaned_data.get("guardian_first_name") or ""
                guardian_last = cleaned_data.get("guardian_last_name") or ""
                verified_guardian_name = getattr(self, "_verified_guardian_name", None)

                if guardian_id:
                    Guardian.objects.update_or_create(
                        student=student,
                        defaults={
                            "name": verified_guardian_name or f"{guardian_first} {guardian_last}".strip(),
                            "guardian_id_number": guardian_id,
                            "relationship": "Parent",
                            "occupation": "",
                            "income": 0,
                            "guardian_phone": "",
                        },
                    )
        except Exception:
            # avoid failing signup due to guardian creation hiccups; log in real app
            pass

        return student



# ========================
# User Form
# ========================
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']



# ========================
# Officer User Form
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


# ========================
# Officer Profile Form (Manager creates officer)
# ========================
class OfficerProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    can_manage_content = forms.BooleanField(
        required=False,
        label="Can Manage Content",
        help_text="Allow this officer to manage slides, banners, success stories, and branding."
    )

    class Meta:
        model = OfficerProfile
        fields = ['phone', 'profile_pic', 'designation', 'can_manage_content']
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
        user = getattr(self.instance, "user", None)
        if email:
            qs = User.objects.filter(email=email)
            if user and user.pk:
                qs = qs.exclude(pk=user.pk)
            if qs.exists():
                self.add_error("email", "This email address is already in use.")
        return cleaned_data

    def save(self, commit=True, creator=None):
        officer = super().save(commit=False)
        # Assign created_by only if provided (i.e., manager creating officer)
        if creator and not officer.pk:
            officer.created_by = creator
        email = self.cleaned_data.get('email')
        if email and hasattr(officer, 'user'):
            officer.user.email = email
            officer.user.save()
        if commit:
            officer.save()
        return officer


# ========================
# Officer Self Profile Form (officer updates own profile)
# ========================
class OfficerSelfProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = OfficerProfile
        fields = ['phone', 'profile_pic']  # Note: no can_manage_content here
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
        user = getattr(self.instance, "user", None)
        if email:
            qs = User.objects.filter(email=email)
            if user and user.pk:
                qs = qs.exclude(pk=user.pk)
            if qs.exists():
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


class SupportRequestForm(forms.ModelForm):
    class Meta:
        model = SupportRequest
        fields = ['subject', 'message']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief summary of your issue'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe your issue in detail'}),
        }


from django import forms
from bursary.models import Banner, LandingSlide, SuccessStory, Announcement
from django.core.exceptions import ValidationError

class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ["image", "title", "caption", "order", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "caption": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(),
        }

class LandingSlideForm(forms.ModelForm):
    class Meta:
        model = LandingSlide
        fields = ["headline", "subheadline", "button_text", "button_url", "image", "order", "is_active"]
        widgets = {
            "headline": forms.TextInput(attrs={"class": "form-control"}),
            "subheadline": forms.TextInput(attrs={"class": "form-control"}),
            "button_text": forms.TextInput(attrs={"class": "form-control"}),
            "button_url": forms.URLInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }

class SuccessStoryForm(forms.ModelForm):
    class Meta:
        model = SuccessStory
        fields = ["title", "description", "image", "order", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "message", "image", "pinned", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "pinned": forms.CheckboxInput(),
            "is_active": forms.CheckboxInput(),
        }


from bursary.models import SiteProfile

class SiteProfileForm(forms.ModelForm):
    class Meta:
        model = SiteProfile
        fields = ["branding_name", "branding_logo", "application_deadline"]
        widgets = {
            "branding_name": forms.TextInput(attrs={"class": "form-control"}),
            "application_deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
