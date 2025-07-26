from django import forms
from .models import Student, BursaryApplication, SupportingDocument, Guardian, Sibling, Ward, OfficerProfile

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'full_name', 'id_number', 'admission_number', 'phone', 'email',
            'institution', 'course', 'year_of_study', 'category', #'profile_pic',
            
        ]

    def clean_profile_pic(self):
        pic = self.cleaned_data.get('profile_pic')

        if pic:
            # Restrict file size (2MB = 2 * 1024 * 1024 bytes)
            max_size = 2 * 1024 * 1024
            if pic.size > max_size:
                raise ValidationError("Profile picture must be under 2MB.")

            # Restrict file types
            valid_types = ['image/jpeg', 'image/png']
            if pic.content_type not in valid_types:
                raise ValidationError("Only JPEG and PNG images are allowed.")

        return pic

class GuardianForm(forms.ModelForm):
    class Meta:
        model = Guardian
        fields = ['name', 'relationship', 'guardian_id_number', 'occupation', 'income', 'guardian_phone']

class SiblingForm(forms.ModelForm):
    class Meta:
        model = Sibling
        fields = ['name', 'school', 'class_level']

class BursaryApplicationForm(forms.ModelForm):
    class Meta:
        model = BursaryApplication
        fields = [
            'constituency',  # this will be disabled in __init__
            'ward',
            'fees_required',
            'fees_paid',
            'amount_requested',
            #'supporting_doc',
        ]

    def __init__(self, *args, **kwargs):
        student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)

        # Make the constituency field read-only
        if student:
            self.fields['constituency'].initial = student.constituency
            self.fields['constituency'].disabled = True
        
        # Make application_deadline field read-only as well (if you are passing this field)
        if 'application_deadline' in self.fields:
            self.fields['application_deadline'].disabled = True

        # Set the constituency field's value to the student's constituency (if available)
        if student and student.constituency:
            self.fields['constituency'].initial = student.constituency
            # Filter the wards based on the student's constituency
            self.fields['ward'].queryset = Ward.objects.filter(constituency=student.constituency)
        else:
            # If no constituency, disable or clear ward field options
            self.fields['ward'].queryset = Ward.objects.none()

    # Optionally, you can add validation to ensure that the constituency is passed correctly
    def clean_constituency(self):
        constituency = self.cleaned_data.get('constituency')
        if not constituency:
            raise forms.ValidationError('Please select a valid constituency.')
        return constituency

class SupportingDocumentForm(forms.ModelForm):
    class Meta:
        model = SupportingDocument
        fields = ['document_type', 'file']



from django.core.exceptions import ValidationError

class StudentSignupForm(UserCreationForm):
    username = forms.CharField(
        label="Admission Number",
        max_length=150,
        required=True,
        help_text="Enter your unique admission number (this will be your username)"
    )
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        help_texts = {
            'username': 'Use your Admission Number as the username',
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("This admission number is already taken.")
        return username

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not any(char.isupper() for char in password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not any(char.isdigit() for char in password):
            raise ValidationError("Password must contain at least one number.")
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/~`" for char in password):
            raise ValidationError("Password must contain at least one special character.")
        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        return password2



class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']


class MinimalStudentSignupForm(UserCreationForm):
    admission_number = forms.CharField(label="Admission Number", max_length=50)

    class Meta:
        model = User
        fields = ['admission_number', 'password1', 'password2']

    def clean_admission_number(self):
        admission_number = self.cleaned_data['admission_number']
        if Student.objects.filter(admission_number=admission_number).exists():
            raise ValidationError("A student with this admission number already exists.")
        return admission_number

    def save(self, commit=True):
        admission_number = self.cleaned_data['admission_number']
        user = super().save(commit=False)
        user.username = admission_number
        if commit:
            user.save()
            Student.objects.create(
                user=user,
                full_name='',
                id_number='',
                phone='',
                email='',
                institution='',
                course='',
                year_of_study='',
                category='boarding',
                has_disability=False,
                admission_number=admission_number,
            )
        return user



class OfficerUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True, help_text="Set a password for this officer.")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

class OfficerProfileForm(forms.ModelForm):
    class Meta:
        model = OfficerProfile
        fields = ['bursary_type', 'designation', 'phone', 'profile_pic']