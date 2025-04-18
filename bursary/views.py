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
    SupportingDocumentForm, UserForm, StudentSignupForm, MinimalStudentSignupForm, SiblingForm
)
from .models import (
    Student, Guardian, Sibling, BursaryApplication,
    SupportingDocument, SiteProfile, OfficerProfile, Constituency, StudentProfile
)
from .sms_utils import send_sms
from .email_utils import send_application_email

from django.views.decorators.http import require_POST

from django.db.models import Count

from django.utils import timezone

from django.forms import modelformset_factory

from django.contrib.sites.shortcuts import get_current_site


# ========================
# Student Bursary Application View
# ========================
@login_required
def apply_bursary(request):
    site_profile = SiteProfile.objects.first()
    application_deadline = None

    if site_profile:
        application_deadline = site_profile.application_deadline

        if not site_profile.is_application_open():
            return render(request, 'bursary/deadline_closed.html', {
                'application_deadline': application_deadline
            })

    student = Student.objects.filter(admission_number=request.user.username).first()

    # 👉 Assign student constituency if not already set
    if student and not student.constituency:
        student.constituency = site_profile.constituency
        student.save()

    if student and BursaryApplication.objects.filter(student=student).exists():
        return render(request, 'bursary/already_applied.html')

    SiblingFormSet = modelformset_factory(Sibling, fields=('name', 'school', 'class_level'), extra=1, can_delete=True)

    if request.method == 'POST':
        student_form = StudentForm(request.POST, instance=student)
        guardian_form = GuardianForm(request.POST)
        application_form = BursaryApplicationForm(request.POST, request.FILES, student=student)
        sibling_formset = SiblingFormSet(request.POST)
        supporting_document_form = SupportingDocumentForm(request.POST, request.FILES)

        if all([student_form.is_valid(), application_form.is_valid(), guardian_form.is_valid(), sibling_formset.is_valid()]):
            student = student_form.save()

            guardian = guardian_form.save(commit=False)
            guardian.student = student
            guardian.save()

            application = application_form.save(commit=False)
            application.student = student
            application.constituency = student.constituency  # Auto-assign student's constituency
            application.bursary_type = 'constituency'
            application.has_disability = request.POST.get("has_disability") == "on"
            application.disability_details = request.POST.get("disability_details", "")
            application.received_bursary_before = request.POST.get("received_bursary_before") == "on"
            application.previous_bursary_details = request.POST.get("previous_bursary_details", "")
            application.save()

            for sibling_form in sibling_formset:
                if sibling_form.cleaned_data and not sibling_form.cleaned_data.get('DELETE'):
                    sibling = sibling_form.save(commit=False)
                    sibling.student = student
                    sibling.save()

            for file in request.FILES.getlist('files'):
                SupportingDocument.objects.create(
                    application=application,
                    file=file,
                    document_type='other'
                )

            send_application_email(student, application)
            send_sms(student.phone, "Your bursary application has been received. You will be notified after review.")

            messages.success(request, "Application submitted successfully!")
            return redirect('application_preview')
    else:
        student_form = StudentForm(instance=student)
        guardian_form = GuardianForm()
        application_form = BursaryApplicationForm(student=student)
        sibling_formset = SiblingFormSet(queryset=Sibling.objects.none())
        supporting_document_form = SupportingDocumentForm()

    return render(request, 'bursary/apply.html', {
        'student_form': student_form,
        'application_form': application_form,
        'guardian_form': guardian_form,
        'sibling_formset': sibling_formset,
        'supporting_document_form': supporting_document_form,
        'application_deadline': application_deadline,
    })

# ========================
# Student Signup
# ========================
def signup_view(request):
    if request.method == 'POST':
        form = StudentSignupForm(request.POST)
        if form.is_valid():
            user = form.save()

            # ✅ Create the StudentProfile
            profile, created = StudentProfile.objects.get_or_create(user=user)
            if created:
                print("✅ StudentProfile created for:", user.username)
            else:
                print("ℹ️ StudentProfile already exists for:", user.username)

            # ✅ Create the Student record (to avoid redirection issues)
            student, created = Student.objects.get_or_create(
                user=user,
                admission_number=user.username,
                defaults={
                    'full_name': '',
                    'id_number': f'DUMMY{user.id}',  # ✅ Prevent duplicate empty id_number
                    'phone': '',
                    'email': user.email,
                    'institution': '',
                    'course': '',
                    'year_of_study': '',
                    'category': 'boarding',
                    'has_disability': False,
                    'previous_bursary': False,
                }
            )
            if created:
                print("✅ Student record created for:", user.username)
            else:
                print("ℹ️ Student record already exists for:", user.username)

            messages.success(request, "Signup successful. Please log in.")
            return redirect('student_login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StudentSignupForm()

    return render(request, 'bursary/signup.html', {'form': form})



def student_login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        remember = request.POST.get('remember_me')

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if not remember:
                request.session.set_expiry(0)

            # 🚨 Check if StudentProfile exists (not just user)
            if StudentProfile.objects.filter(user=user).exists():
                return redirect('student_dashboard')

            elif OfficerProfile.objects.filter(user=user).exists():
                messages.error(request, "This is not the login page for officers.")
                return redirect('staff_login')

            else:
                messages.error(request, "Profile not found. Please complete your signup.")
                return redirect('student_signup')

        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'bursary/login.html', {'form': form})


class StaffLoginView(LoginView):
    template_name = 'bursary/staff_login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_staff:
            messages.error(self.request, "You are not authorized to log in here.")
            return self.form_invalid(form)
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
    constituency_filter = request.GET.get('constituency', '')

    applications = BursaryApplication.objects.select_related('student', 'constituency')
    application_type = 'constituency'

    # Filter applications by officer role
    if request.user.is_superuser:
        applications = applications.filter(bursary_type=application_type)
    else:
        try:
            profile = OfficerProfile.objects.get(user=request.user)
            applications = applications.filter(
                bursary_type=profile.bursary_type,
                constituency=profile.constituency
            )
            application_type = profile.bursary_type
        except OfficerProfile.DoesNotExist:
            messages.error(request, "No Officer Profile found for this user.")
            return redirect('admin_dashboard')

    # Filter by status or constituency if selected
    if constituency_filter:
        applications = applications.filter(constituency__name=constituency_filter)
    if status_filter:
        applications = applications.filter(status=status_filter)

    # Compute stats
    total_apps = applications.count()
    total_requested = applications.aggregate(Sum('amount_requested'))['amount_requested__sum'] or 0
    total_funded = applications.filter(status='approved').aggregate(Sum('amount_requested'))['amount_requested__sum'] or 0
    status_data = {
        'Pending': applications.filter(status='pending').count(),
        'Approved': applications.filter(status='approved').count(),
        'Rejected': applications.filter(status='rejected').count(),
    }

    all_constituencies = Constituency.objects.all()

    return render(request, 'bursary/admin_reports.html', {
        'applications': applications,
        'total_apps': total_apps,
        'total_requested': total_requested,
        'total_funded': total_funded,
        'status_data': status_data,
        'all_constituencies': all_constituencies,
        'selected_constituency': constituency_filter,
        'selected_status': status_filter,
        'application_type': application_type,
    })


@login_required
def student_dashboard(request):
    try:
        student = Student.objects.get(email=request.user.email)
    except Student.DoesNotExist:
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

    return render(request, 'bursary/student_dashboard.html', {
        'student': student,
        'application_status': application_status,
        'application': application,  # Keep existing applications for future references
    })



# ========================
# Student Profile View
# ========================
@login_required
def student_profile_view(request):
    student = Student.objects.filter(admission_number=request.user.username).first()
    if not student:
        messages.warning(request, "We couldn’t find your profile info yet. Please apply first.")
        return redirect('student_dashboard')  # Adjust as needed
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
        documents = SupportingDocument.objects.filter(application=application)

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
        'documents': documents,
    })




# ========================
# Export Applications as CSV
# ========================
@staff_member_required
def export_applications_csv(request):
    applications = BursaryApplication.objects.select_related('student')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bursary_applications.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Full Name', 'Admission No', 'ID No', 'Institution', 'Course',
        'Fees Required', 'Fees Paid', 'Amount Requested',
        'Status', 'Phone', 'Email', 'Submission Date'
    ])

    for app in applications:
        s = app.student
        writer.writerow([
            s.full_name,
            s.admission_number,
            s.id_number,
            s.institution,
            s.course,
            app.fees_required,
            app.fees_paid,
            app.amount_requested,
            app.status.title(),
            s.phone,
            s.email,
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
        documents = SupportingDocument.objects.filter(application=application)
    except:
        return redirect('apply_bursary')

    return render_to_pdf('bursary/pdf_template.html', {
        'student': student,
        'application': application,
        'guardian': guardian,
        'siblings': siblings,
        'documents': documents,
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

    # Only allow if this officer is authorized
    try:
        officer = OfficerProfile.objects.get(user=request.user)
        if application.constituency != officer.constituency or application.bursary_type != officer.bursary_type:
            messages.error(request, "You're not allowed to view this application.")
            return redirect('officer_dashboard')
    except OfficerProfile.DoesNotExist:
        messages.error(request, "Access denied.")
        return redirect('login')

    return render(request, 'bursary/application_detail.html', {
        'application': application,
    })

@require_POST
@login_required
def update_application_status(request, application_id):
    application = get_object_or_404(BursaryApplication, id=application_id)
    new_status = request.POST.get('status')

    if new_status not in ['approved', 'rejected']:
        messages.error(request, "Invalid status.")
        return redirect('officer_dashboard')

    officer = OfficerProfile.objects.get(user=request.user)
    if application.constituency != officer.constituency or application.bursary_type != officer.bursary_type:
        messages.error(request, "Not authorized to update this application.")
        return redirect('officer_dashboard')

    application.status = new_status
    application.feedback = request.POST.get('feedback', '')
    application.save()

    messages.success(request, f"Application marked as {new_status}.")
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