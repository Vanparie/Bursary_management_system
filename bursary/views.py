from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.template.loader import get_template
from django.contrib.staticfiles import finders
from django.urls import reverse_lazy

import csv
from xhtml2pdf import pisa

# Local imports: forms, models, SMS/email utilities
from .forms import (
    StudentForm, GuardianForm, BursaryApplicationForm,
    SupportingDocumentForm, UserForm, StudentSignupForm, MinimalStudentSignupForm, SiblingForm, OfficerUserForm, OfficerProfileForm
)
from .models import (
    Student, Guardian, Sibling, BursaryApplication,
    SupportingDocument, SiteProfile, OfficerProfile, Constituency, StudentProfile, Ward, OfficerActivityLog
)
from .sms_utils import send_sms
from .email_utils import send_application_email

from django.views.decorators.http import require_POST

from django.db.models import Count

from django.utils import timezone

from django.forms import modelformset_factory

from django.contrib.sites.shortcuts import get_current_site

from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash


def home(request):
    # Fetch the first SiteProfile or adjust based on your specific use case
    branding = SiteProfile.objects.first()  # Adjust as needed (e.g., filter by county or other criteria)

    # Pass the 'branding' object to the context
    context = {
        'branding': branding,
    }
    
    return render(request, 'base.html', context)


# ========================
# Student Bursary Application View
# ========================
from django.forms import modelformset_factory

@login_required
def apply_bursary(request):
    site_profile = SiteProfile.objects.first()
    application_deadline = site_profile.application_deadline if site_profile else None

    if site_profile and not site_profile.is_application_open():
        return render(request, 'bursary/deadline_closed.html', {
            'application_deadline': application_deadline
        })

    student = Student.objects.filter(admission_number=request.user.username).first()

    # Assign student constituency if not already set
    if student and not student.constituency and site_profile:
        student.constituency = site_profile.constituency
        student.save()

    if student and BursaryApplication.objects.filter(student=student).exists():
        return render(request, 'bursary/already_applied.html')

    # ✅ Define formsets
    SiblingFormSet = modelformset_factory(Sibling, fields=('name', 'school', 'class_level'), extra=2, can_delete=True)
    SupportingDocumentFormSet = modelformset_factory(SupportingDocument, fields=('document_type', 'file'), extra=3, can_delete=True)

    if request.method == 'POST':
        student_form = StudentForm(request.POST, instance=student)
        guardian_form = GuardianForm(request.POST)
        application_form = BursaryApplicationForm(request.POST, request.FILES, student=student)
        sibling_formset = SiblingFormSet(request.POST)
        document_formset = SupportingDocumentFormSet(request.POST, request.FILES, queryset=SupportingDocument.objects.none())

        if all([
            student_form.is_valid(), application_form.is_valid(), guardian_form.is_valid(),
            sibling_formset.is_valid(), document_formset.is_valid()
        ]):
            student = student_form.save(commit=False)
            student.has_disability = request.POST.get("has_disability") == "on"
            student.disability_details = request.POST.get("disability_details", "")
            student.previous_bursary = request.POST.get("received_bursary_before") == "on"
            student.previous_bursary_details = request.POST.get("previous_bursary_details", "")
            student.save()

            # Clear old guardians and siblings
            #Guardian.objects.filter(student=student).delete()
            Sibling.objects.filter(student=student).delete()

            Guardian.objects.update_or_create(
                student=student,
                defaults={
                    'name': guardian_form.cleaned_data['name'],
                    'relationship': guardian_form.cleaned_data['relationship'],
                    'guardian_id_number': guardian_form.cleaned_data['guardian_id_number'],
                    'occupation': guardian_form.cleaned_data['occupation'],
                    'income': guardian_form.cleaned_data['income'],
                    'guardian_phone': guardian_form.cleaned_data['guardian_phone'],
                }
            )

            application = application_form.save(commit=False)
            application.student = student
            application.constituency = student.constituency
            application.bursary_type = 'constituency'
            application.save()

            for sibling_form in sibling_formset:
                if sibling_form.cleaned_data and not sibling_form.cleaned_data.get('DELETE'):
                    sibling = sibling_form.save(commit=False)
                    sibling.student = student
                    sibling.save()

            for doc_form in document_formset:
                if doc_form.cleaned_data and not doc_form.cleaned_data.get('DELETE'):
                    doc = doc_form.save(commit=False)
                    doc.application = application
                    doc.save()
            
            #messages.success(request, "✅ Your bursary application has been submitted successfully!")
            send_application_email(student, application)
            send_sms(student.phone, "Your bursary application has been received. You will be notified after review.")

            return redirect('application_preview')

    else:
        student_form = StudentForm(instance=student)
        guardian_form = GuardianForm()
        application_form = BursaryApplicationForm(student=student)
        sibling_formset = SiblingFormSet(queryset=Sibling.objects.none())
        document_formset = SupportingDocumentFormSet(queryset=SupportingDocument.objects.none())

    return render(request, 'bursary/apply.html', {
        'student_form': student_form,
        'application_form': application_form,
        'guardian_form': guardian_form,
        'sibling_formset': sibling_formset,
        'document_formset': document_formset,
        'application_deadline': application_deadline,
    })



# ========================
# Student Signup
# ========================

# from .forms import StudentSignupForm  # keep this import

def signup_view(request):
    # 🚫 Public student registration is disabled
    messages.warning(request, "Student registration is currently disabled. Please contact the admin.")
    return redirect('student_login')


def student_login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        remember = request.POST.get('remember_me')

        if form.is_valid():
            user = form.get_user()

            # ✅ Only allow login if user is linked to a StudentProfile
            if StudentProfile.objects.filter(user=user).exists():
                login(request, user)

                if not remember:
                    request.session.set_expiry(0)  # Session expires on browser close

                # ✅ Check if student must change password
                student = Student.objects.filter(user=user).first()
                if student and student.must_change_password:
                    return redirect('change_password')  # Redirect to change password

                return redirect('student_dashboard')

            elif OfficerProfile.objects.filter(user=user).exists():
                messages.error(request, "Officers must use the staff login page.")
                return redirect('staff_login')

            else:
                messages.error(request, "You are not registered as a student.")
                return redirect('student_login')  # Stay on login page

        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'bursary/login.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Set must_change_password to False
            student = Student.objects.get(user=request.user)
            student.must_change_password = False
            student.save()

            update_session_auth_hash(request, request.user)
            # ✅ Set a session flag instead of immediate message
            request.session['show_password_message'] = True

            return redirect('student_dashboard')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'bursary/change_password.html', {'form': form})



class StaffLoginView(LoginView):
    template_name = 'bursary/staff_login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        log_officer_action(user, 'login', 'Officer logged in') 
        if not user.is_staff:
            messages.error(self.request, "You are not authorized to log in here.")
            return self.form_invalid(form)
        return super().form_valid(form)

        if hasattr(user, 'officerprofile') and not user.officerprofile.is_active:
            logout(self.request)
            messages.error(self.request, "Your officer account is inactive. Contact administrator.")
            return redirect('staff_login')

        log_officer_action(user, 'login', 'Officer logged in')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('admin_dashboard')  # Or whatever URL is appropriate

# ========================
# Landing Page View
# ========================
def landing_page(request):
    # Fetch the site profile, assuming it's available in the context
    site_profile = SiteProfile.objects.first()
    return render(request, 'bursary/landing.html', {'site_profile': site_profile})

    #return render(request, 'bursary/landing.html', {'application_deadline': application_deadline})

# ========================
# Admin/Officer Dashboard (Application List and Stats)
# ========================
@staff_member_required
def admin_dashboard(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    ward_filter = request.GET.get('ward', '')

    applications = BursaryApplication.objects.select_related('student', 'constituency')
    application_type = 'constituency'  # or 'county' based on your setup

    # Filter applications by officer role
    if request.user.is_superuser:
        applications = applications.filter(bursary_type=application_type)
        wards = Ward.objects.none()  # Superuser doesn't need ward filter
    else:
        try:
            profile = OfficerProfile.objects.get(user=request.user)
            constituency = profile.constituency
            applications = applications.filter(bursary_type=profile.bursary_type, constituency=constituency)
            application_type = profile.bursary_type

            # ✅ Get all Wards for the officer’s constituency
            wards = Ward.objects.filter(constituency=constituency)

            # ✅ Filter by Ward if selected
            if ward_filter:
                applications = applications.filter(ward__id=ward_filter)

        except OfficerProfile.DoesNotExist:
            messages.error(request, "No Officer Profile found for this user.")
            return redirect('landing_page')

    # ✅ Filter by status if provided
    if status_filter:
        applications = applications.filter(status=status_filter)

    # ✅ Compute summary stats
    total_apps = applications.count()
    total_requested = applications.aggregate(Sum('amount_requested'))['amount_requested__sum'] or 0
    #total_awarded = applications.aggregate(Sum('amount_awarded'))['amount_awarded__sum'] or 0
    total_approved = applications.filter(status='approved').aggregate(Sum('amount_awarded'))['amount_awarded__sum'] or 0
    status_data = {
        'Pending': applications.filter(status='pending').count(),
        'Approved': applications.filter(status='approved').count(),
        'Rejected': applications.filter(status='rejected').count(),
    }

    return render(request, 'bursary/admin_reports.html', {
        'applications': applications,
        'total_apps': total_apps,
        'total_requested': total_requested,
        'total_approved': total_approved,
        'status_data': status_data,
        'wards': wards,
        'selected_ward': ward_filter,
        'selected_status': status_filter,
        'application_type': application_type,
    })


@login_required
def student_dashboard(request):
    try:
        # 🔄 Use the user foreign key to fetch the student
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('student_signup')  # Or any fallback

    # Get the student's bursary application (if any)
    application = BursaryApplication.objects.filter(student=student).first()

    # Initialize the application status message
    if application:
        if application.status == 'pending':
            application_status = 'Your application is still pending.'
        elif application.status == 'verified':
            application_status = 'Your application has been verified.'
        elif application.status == 'approved':
            application_status = 'Your application has been approved.'
        elif application.status == 'rejected':
            application_status = 'Your application has been rejected.'
    else:
        application_status = 'You have not submitted any bursary application yet.'

    # 🔥 Force message queue to clear any duplicate leftovers
    #list(messages.get_messages(request))
    if request.session.pop('show_password_message', False):
        messages.success(request, 'Password updated successfully.')


    return render(request, 'bursary/student_dashboard.html', {
        'student': student,
        'application_status': application_status,
        'application': application,
    })



# ========================
# Student Profile View
# ========================
@login_required
def student_profile_view(request):
    #student = Student.objects.filter(admission_number=request.user.username).first()
    student = Student.objects.get(user=request.user)
    #if not student:
     #   messages.warning(request, "We couldn’t find your profile info yet. Please apply first.")
      #  return redirect('student_dashboard')  # Adjust as needed
    return render(request, 'bursary/student_profile_view.html', {'student': student})

# ========================
# Student Profile Edit View
# ========================
@login_required
def student_profile_edit(request):
    student = Student.objects.filter(admission_number=request.user.username).first()
    user = request.user

    if request.method == 'POST':
        student_form = StudentForm(request.POST, instance=student)
        user_form = UserForm(request.POST, instance=user)

        if student_form.is_valid() and user_form.is_valid():
            student_form.save()
            user_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('student_profile')
    else:
        student_form = StudentForm(instance=student)
        user_form = UserForm(instance=user)

    return render(request, 'bursary/student_profile_edit.html', {
        'student_form': student_form,
        'user_form': user_form
    })

# ========================
# Application Preview View
# ========================
@login_required
def application_preview(request):
    try:
        student = Student.objects.get(admission_number=request.user.username)
        application = BursaryApplication.objects.get(student=student)

        # If the application is rejected, allow the student to modify it (reapply)
        if application.status == 'rejected':
            messages.info(request, "Your previous application was rejected. You can update it.")
            return redirect('apply_bursary')  # Redirect to apply_bursary form

        # Fetch guardian and siblings details
        guardians = Guardian.objects.filter(student=student)  # Multiple guardians
        siblings = Sibling.objects.filter(student=student)
        supporting_documents = SupportingDocument.objects.filter(application=application)

    except BursaryApplication.DoesNotExist:
        # If no application exists, redirect to the application form
        messages.error(request, "You have not submitted an application yet.")
        return redirect('apply_bursary')

    except Exception as e:
        # Catch any other exceptions and log the error (optional)
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('student_dashboard')

    # Render the preview page with the student, application, guardian, etc.
    return render(request, 'bursary/application_preview.html', {
        'student': student,
        'application': application,
        'guardians': guardians,  # Pass the list of guardians
        'siblings': siblings,
        'supporting_documents': supporting_documents,
    })




# ========================
# Export Applications as CSV
# ========================
@staff_member_required
def export_applications_csv(request):
    applications = BursaryApplication.objects.select_related('student', 'constituency')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="bursary_applications.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Full Name', 'Admission No', 'ID No', 'Institution', 'Course', 'Year of Study',
        'Constituency', 'Fees Required', 'Fees Paid', 'Amount Requested', 'Amount Awarded',
        'Status', 'Feedback', 'Phone', 'Email', 'Guardian Name', 'Guardian Income', 'Submission Date'
    ])

    for app in applications:
        student = app.student
        guardian = getattr(student, 'guardian', None)

        writer.writerow([
            student.full_name,
            student.admission_number,
            student.id_number,
            student.institution,
            student.course,
            student.year_of_study,
            app.constituency.name if app.constituency else '',
            app.fees_required or 0,
            app.fees_paid or 0,
            app.amount_requested or 0,
            app.amount_awarded or 0,
            app.status.title(),
            app.feedback or '',
            student.phone,
            student.email,
            guardian.name if guardian else '',
            guardian.income if guardian else '',
            app.date_applied.strftime('%Y-%m-%d %H:%M')
        ])

    return response


# ========================
# Generate PDF Preview
# ========================
def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html, dest=result, link_callback=fetch_resources)
    if pisa_status.err:
        return HttpResponse('We had some errors with PDF generation <pre>' + html + '</pre>')
    return result

def fetch_resources(uri, rel):
    # Convert static resource paths for PDF generation
    path = finders.find(uri)
    return path

# ========================
# View PDF Application
# ========================
@login_required
def application_pdf(request):
    try:
        student = Student.objects.get(admission_number=request.user.username)
        application = BursaryApplication.objects.get(student=student)
        guardian = Guardian.objects.get(student=student)
        siblings = Sibling.objects.filter(student=student)
        supporting_documents = SupportingDocument.objects.filter(application=application)
    except:
        return redirect('apply_bursary')

    return render_to_pdf('bursary/pdf_template.html', {
        'student': student,
        'application': application,
        'guardian': guardian,
        'siblings': siblings,
        'supporting_documents': supporting_documents,
    })



@login_required
def officer_dashboard(request):
    try:
        officer = OfficerProfile.objects.get(user=request.user)
    except OfficerProfile.DoesNotExist:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('login')

    # Filter applications based on officer's constituency and bursary type
    applications = BursaryApplication.objects.filter(
        constituency=officer.constituency,
        bursary_type=officer.bursary_type
    ).order_by('-date_applied')

    return render(request, 'bursary/officer_dashboard.html', {
        'applications': applications,
    })



@login_required
def officer_profile_view(request):
    try:
        officer_profile = OfficerProfile.objects.get(user=request.user)
    except OfficerProfile.DoesNotExist:
        messages.error(request, "We couldn’t find your officer profile.")
        return redirect('officer_dashboard')

    return render(request, 'bursary/officer_profile.html', {
        'officer': officer_profile,
    })



@login_required
def application_detail(request, application_id):
    application = get_object_or_404(BursaryApplication, id=application_id)

    # Authorization check
    try:
        officer = OfficerProfile.objects.get(user=request.user)
        if application.constituency != officer.constituency or application.bursary_type != officer.bursary_type:
            messages.error(request, "You're not allowed to view this application.")
            return redirect('officer_dashboard')
    except OfficerProfile.DoesNotExist:
        messages.error(request, "Access denied.")
        return redirect('login')

    # ✅ Fetch associated guardians
    guardians = Guardian.objects.filter(student=application.student)

    # ✅ Fetch siblings for completeness
    siblings = application.student.sibling_set.all()

    # ✅ Fetch supporting documents
    supporting_documents = application.supportingdocument_set.all()
    # supporting_documents = SupportingDocument.objects.filter(application=application)


    return render(request, 'bursary/application_detail.html', {
        'application': application,
        'guardians': guardians,
        'siblings': siblings,
        'supporting_documents': supporting_documents,
    })


@require_POST
@login_required
def update_application_status(request, application_id):
    application = get_object_or_404(BursaryApplication, id=application_id)
    new_status = request.POST.get('status')

    if new_status not in ['approved', 'rejected']:
        messages.error(request, "Invalid status.")
        return redirect('officer_dashboard')

    try:
        officer = OfficerProfile.objects.get(user=request.user)
    except OfficerProfile.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect('officer_dashboard')

    if application.constituency != officer.constituency or application.bursary_type != officer.bursary_type:
        messages.error(request, "Not authorized to update this application.")
        return redirect('officer_dashboard')

    application.status = new_status
    application.feedback = request.POST.get('feedback', '')

    amount_awarded = request.POST.get('amount_awarded')
    application.amount_awarded = int(amount_awarded) if amount_awarded else None

    application.save()

    log_officer_action(request.user, 'change_status', f"Updated application #{application.id} to {new_status}")

    messages.success(request, f"Application #{application.id} marked as {new_status}.")
    return redirect('officer_dashboard')


# Admin login view
def admin_login_view(request):
    if request.user.is_authenticated:
        return redirect('admin_dashboard')  # or wherever you want to redirect authenticated users

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser:  # Check if the user is an admin
                login(request, user)
                return redirect('admin_dashboard')  # Redirect to admin dashboard or home page
            else:
                messages.error(request, "You do not have admin privileges.")
                return redirect('admin_login')
    else:
        form = AuthenticationForm()

    return render(request, 'bursary/admin_login.html', {'form': form})



@login_required
def admin_reports(request):
    # Check if the user is a superuser (admin)
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to view reports.")
        return redirect('admin_login')

    # Initialize context dictionary for the report data
    context = {}

    # Fetch data to display in the report:
    
    # Total number of bursary applications
    total_applications = BursaryApplication.objects.count()

    # Count applications by status (e.g., pending, verified, approved, rejected)
    application_status_counts = BursaryApplication.objects.values('status').annotate(count=Count('status'))

    # Count applications by bursary type (county, constituency)
    bursary_type_counts = BursaryApplication.objects.values('bursary_type').annotate(count=Count('bursary_type'))

    # Fetch specific applications (optional): For example, get all pending applications
    pending_applications = BursaryApplication.objects.filter(status='pending')

    # Optionally, filter applications by date range (if provided)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        filtered_applications = BursaryApplication.objects.filter(date_applied__range=[start_date, end_date])
    else:
        filtered_applications = BursaryApplication.objects.all()

    # Add the data to the context
    context['total_applications'] = total_applications
    context['application_status_counts'] = application_status_counts
    context['bursary_type_counts'] = bursary_type_counts
    context['pending_applications'] = pending_applications
    context['filtered_applications'] = filtered_applications

    # Render the report page with the data
    return render(request, 'bursary/admin_reports.html', context)


from .models import Student, BursaryApplication

import io
from django.http import FileResponse
from django.template.loader import get_template
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
import weasyprint

from .models import Student, BursaryApplication, Guardian, Sibling

@login_required
def application_pdf(request):
    student = get_object_or_404(Student, user=request.user)
    application = get_object_or_404(BursaryApplication, student=student)
    guardian = get_object_or_404(Guardian, student=student)
    siblings = Sibling.objects.filter(student=student)

    template = get_template('bursary/pdf_template.html')
    html = template.render({
        'student': student,
        'application': application,
        'guardian': guardian,
        'siblings': siblings
    })

    pdf_file = weasyprint.HTML(string=html).write_pdf()

    return FileResponse(io.BytesIO(pdf_file), content_type='application/pdf', filename='bursary_application.pdf')



def submit_bursary_application(request):
    student = request.user.student  # Assuming you're using the logged-in user as the student
    # Check if the student has already submitted an application
    existing_application = BursaryApplication.objects.filter(student=student).first()

    if existing_application:
        # If the student has already applied, update or show a message
        # (We update the application status if needed, e.g. if it was 'pending' or 'verified')
        existing_application.status = 'pending'  # Or any other logic
        existing_application.save()
    else:
        # Create a new application if none exists
        BursaryApplication.objects.create(
            student=student,
            bursary_type='constituency',  # or 'county' depending on the case
            fees_required=10000,  # Example fee value
            fees_paid=0,  # Example fee value
            amount_requested=10000,  # Example amount requested
            status='pending',  # Default status
            date_applied=timezone.now(),
        )
    
    return redirect('student_dashboard')  # Redirect to the dashboard after submission



from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.urls import reverse_lazy

class StudentPasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'bursary/password_change.html'
    success_url = reverse_lazy('student_profile')  # or your actual named URL
    #success_message = "✅ Your password has been changed successfully."

    def form_valid(self, form):
        #Clear any existing success messages
        storage = messages.get_messages(self.request)
        for _ in storage:
            pass  # just iterating clears old messages

        messages.success(self.request, "Password updated successfully.")
        return super().form_valid(form)


@login_required
def delete_profile_picture(request):
    student = request.user.student
    if student.profile_pic:
        student.profile_pic.delete(save=False)
        student.profile_pic = None
        student.save()
        messages.success(request, "Profile picture deleted successfully.")
    else:
        messages.info(request, "No profile picture to delete.")
    return redirect('student_profile')



from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404

@staff_member_required
def manage_officers(request):
    profile = request.user.officerprofile
    if not profile.is_manager:
        messages.error(request, "Access denied. Only managers can manage officers.")
        return redirect('officer_dashboard')

    officers = OfficerProfile.objects.filter(constituency=profile.constituency).select_related('user')

    return render(request, 'bursary/manage_officers.html', {'officers': officers})

from django.contrib.auth.decorators import user_passes_test

def is_senior_officer(user):
    return user.groups.filter(name='SeniorOfficer').exists() or user.is_superuser


@staff_member_required
#@user_passes_test(is_senior_officer)
def add_officer(request):
    profile = request.user.officerprofile
    if not profile.is_manager:
        messages.error(request, "Access denied. Only managers can add officers.")
        return redirect('officer_dashboard')

    if request.method == 'POST':
        user_form = OfficerUserForm(request.POST)
        profile_form = OfficerProfileForm(request.POST, request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.is_staff = True
            user.save()

            officer_profile = profile_form.save(commit=False)
            officer_profile.user = user
            officer_profile.constituency = profile.constituency
            officer_profile.save()

            log_officer_action(request.user, 'add_officer', f"Added officer account for {user.username}")

            messages.success(request, "Officer added successfully.")
            return redirect('manage_officers')
    else:
        user_form = OfficerUserForm()
        profile_form = OfficerProfileForm()

    return render(request, 'bursary/add_officer.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


@staff_member_required
def edit_officer(request, officer_id):
    profile = request.user.officerprofile
    if not profile.is_manager:
        messages.error(request, "Access denied.")
        return redirect('officer_dashboard')

    officer = get_object_or_404(OfficerProfile, id=officer_id, constituency=profile.constituency)

    if request.method == 'POST':
        user_form = OfficerUserForm(request.POST, instance=officer.user)
        profile_form = OfficerProfileForm(request.POST, request.FILES, instance=officer)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            if user_form.cleaned_data['password']:
                user.set_password(user_form.cleaned_data['password'])
            user.save()
            profile_form.save()

            messages.success(request, "Officer updated successfully.")
            return redirect('manage_officers')
    else:
        user_form = OfficerUserForm(instance=officer.user)
        profile_form = OfficerProfileForm(instance=officer)

    return render(request, 'bursary/edit_officer.html', {'user_form': user_form, 'profile_form': profile_form})


@staff_member_required
def delete_officer(request, officer_id):
    profile = request.user.officerprofile
    if not profile.is_manager:
        messages.error(request, "Access denied.")
        return redirect('officer_dashboard')

    officer = get_object_or_404(OfficerProfile, id=officer_id, constituency=profile.constituency)

    if request.method == 'POST':
        officer.user.delete()  # Deletes both User & OfficerProfile due to cascade
        messages.success(request, "Officer deleted.")
        return redirect('manage_officers')

    return render(request, 'bursary/confirm_delete.html', {'officer': officer})


def log_officer_action(officer, action, description=""):
    from .models import OfficerActivityLog
    OfficerActivityLog.objects.create(officer=officer, action=action, description=description)


@staff_member_required
def officer_logs(request):
    logs = OfficerActivityLog.objects.filter(officer=request.user).order_by('-timestamp')
    return render(request, 'bursary/officer_logs.html', {'logs': logs})


@staff_member_required
def export_officer_logs(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="officer_logs.csv"'

    writer = csv.writer(response)
    writer.writerow(['Officer Username', 'Action', 'Description', 'Timestamp'])

    logs = OfficerActivityLog.objects.select_related('officer').order_by('-timestamp')
    for log in logs:
        writer.writerow([log.officer.username, log.action, log.description, log.timestamp])

    return response


@staff_member_required
def officer_reports(request):
    return render(request, 'bursary/officer_reports.html')






# from django.shortcuts import render, redirect
# from django.contrib import messages
# from django.contrib.auth import login
# from django.contrib.auth.models import User
# from bursary.models import Student, SiteProfile
# from bursary.utils import mock_verify_government_id  # Use real API later


# def verify_login(request):
#     site_profile = SiteProfile.objects.first()
#     current_constituency_name = site_profile.constituency.name if site_profile else None

#     if request.method == "POST":
#         student_id = request.POST.get("student_id_number")
#         guardian_id = request.POST.get("guardian_id_number")

#         # ✅ Call mock function with both IDs
#         verification_data = mock_verify_government_id(student_id, guardian_id)

#         if not verification_data:
#             messages.error(request, "❌ Invalid student or guardian ID. Please try again.")
#             return redirect('verify_login')

#         student_data = verification_data.get("student")
#         guardian_data = verification_data.get("guardian")

#         if not student_data:
#             messages.error(request, "❌ Student ID not found in national records.")
#             return redirect('verify_login')

        
#         if student_data["constituency_name"].strip().lower().replace("_", " ") != current_constituency_name.strip().lower():
#             messages.error(request, "❌ You are not eligible to apply in this constituency.")
#             return redirect('verify_login')


#         # ✅ Create User if it doesn't exist
#         user, created = User.objects.get_or_create(username=student_id)
#         if created:
#             user.set_unusable_password()
#             user.save()

#         # ✅ Create Student record if doesn't exist
#         student, created = Student.objects.get_or_create(
#             id_number=student_id,
#             defaults={
#                 "admission_number": student_id if student_id else generate_random_admission_number(),
#                 "full_name": student_data["full_name"],
#                 #"date_of_birth": student_data["dob"],
#                 "constituency": site_profile.constituency,
#                 #"guardian_id": guardian_id,
#                 "user": user
#             }
#         )

#         # ✅ Log the user in
#         login(request, user)
#         return redirect('student_dashboard')

#     return render(request, 'bursary/verify_login.html')

