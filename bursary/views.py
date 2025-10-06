# Standard library
import csv
import io
import json

# Third-party (PDF / report libraries)
import weasyprint
from xhtml2pdf import pisa
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# Django
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView, PasswordChangeView
)
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db import models as dj_models  # if you need alias for Count/Sum etc (optional)
from django.db.models import (
    Q, Sum, Count, Value, DecimalField, OuterRef, Subquery
)
from django.db.models.functions import Coalesce
from django.forms import modelformset_factory
from django.http import HttpResponse, JsonResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt  # keep only if used; not recommended for production
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.staticfiles import finders
from django.shortcuts import render, redirect

# Local app imports (forms, models, utilities)
from .forms import (
    StudentForm, StudentProfileForm, GuardianForm, BursaryApplicationForm,
    SupportingDocumentForm, UserForm, VerifiedStudentSignupForm, SiblingForm,
    OfficerUserForm, OfficerProfileForm, StudentLoginForm, SimplePasswordChangeForm,
    OfficerSelfProfileForm, UpgradeToIDForm, SupportRequestForm
)
from .utils.mock_verification import verify_id, verify_nemis
from .sms_utils import send_sms
from .email_utils import send_application_email

from .models import (
    Student, Guardian, Sibling, BursaryApplication, SupportingDocument,
    SiteProfile, OfficerProfile, Constituency, Ward, OfficerActivityLog,
    SupportRequest, LandingSlide, SuccessStory
)

from functools import wraps
from decimal import Decimal, InvalidOperation
from django.http import HttpResponse, Http404
from django.db.models import Sum


# Notes:
# - csrf_exempt should be removed unless you absolutely need it for a specific endpoint.
# - Multiple PDF libraries (weasyprint, xhtml2pdf/pisa, reportlab) are present because different parts of the code use them;
#   using more than one increases dependencies and maintenance cost — consider consolidating to one (weasyprint is modern/robust).



# ========================
# Home / Landing
# ========================
def home(request):
    """Landing page with active branding."""
    branding = SiteProfile.get_active()
    return render(request, "base.html", {"branding": branding})


# ========================
# Student Bursary Application View
# ========================
@login_required
def apply_bursary(request):
    site_profile = SiteProfile.get_active()
    application_deadline = site_profile.application_deadline if site_profile else None

    if site_profile and not site_profile.is_application_open():
        return render(
            request,
            "bursary/deadline_closed.html",
            {"application_deadline": application_deadline},
        )

    student = (
        Student.objects.select_related("constituency", "county")
        .filter(user=request.user)
        .first()
    )
    if not student:
        messages.error(request, "Student profile not found. Please update your profile first.")
        return redirect("student_profile_edit")

    # Assign constituency from SiteProfile if not set
    if not student.constituency and site_profile and site_profile.constituency:
        student.constituency = site_profile.constituency
        student.save(update_fields=["constituency"])

    # Prevent duplicate applications
    if BursaryApplication.objects.filter(student=student).exists():
        return render(request, "bursary/already_applied.html")

    # Inline formsets
    SiblingFormSet = modelformset_factory(
        Sibling, fields=("name", "school", "class_level"), extra=2, can_delete=True
    )
    SupportingDocumentFormSet = modelformset_factory(
        SupportingDocument, fields=("document_type", "file"), extra=3, can_delete=True
    )

    if request.method == "POST":
        student_form = StudentForm(request.POST, instance=student)
        guardian_form = GuardianForm(request.POST)
        application_form = BursaryApplicationForm(
            request.POST, request.FILES, student=student
        )
        sibling_formset = SiblingFormSet(request.POST, prefix="siblings")
        document_formset = SupportingDocumentFormSet(
            request.POST, request.FILES,
            queryset=SupportingDocument.objects.none(),
            prefix="documents",
        )

        if all([
            student_form.is_valid(),
            guardian_form.is_valid(),
            application_form.is_valid(),
            sibling_formset.is_valid(),
            document_formset.is_valid(),
        ]):
            student_form.save()

            # Save/update guardian (skip if form was left blank)
            if guardian_form.cleaned_data.get("name"):
                Guardian.objects.update_or_create(
                    student=student,
                    defaults=guardian_form.cleaned_data,
                )

            application = application_form.save(commit=False)
            application.student = student
            application.constituency = student.constituency
            application.save()

            # Save siblings
            for sf in sibling_formset:
                if sf.cleaned_data and not sf.cleaned_data.get("DELETE"):
                    sibling = sf.save(commit=False)
                    sibling.student = student
                    sibling.save()

            # Save supporting docs
            for df in document_formset:
                if df.cleaned_data and not df.cleaned_data.get("DELETE"):
                    doc = df.save(commit=False)
                    doc.application = application
                    doc.save()

            # Notifications
            send_application_email(student, application)
            send_sms(
                student.phone,
                "✅ Your bursary application has been received. You will be notified after review.",
            )

            messages.success(request, "✅ Your bursary application has been submitted successfully!")
            return redirect("student_dashboard")

    else:
        student_form = StudentForm(instance=student)
        guardian_form = GuardianForm()
        application_form = BursaryApplicationForm(student=student)
        sibling_formset = SiblingFormSet(queryset=Sibling.objects.none(), prefix="siblings")
        document_formset = SupportingDocumentFormSet(queryset=SupportingDocument.objects.none(), prefix="documents")

    return render(
        request,
        "bursary/apply.html",
        {
            "student_form": student_form,
            "application_form": application_form,
            "guardian_form": guardian_form,
            "sibling_formset": sibling_formset,
            "document_formset": document_formset,
            "application_deadline": application_deadline,
        },
    )


# ========================
# Student Signup (with verification)
# ========================
def signup_view(request):
    site_profile = SiteProfile.get_active()
    if not site_profile:
        messages.error(request, "System is not configured. Please contact admin.")
        return redirect("student_login")

    if request.method == "POST":
        form = VerifiedStudentSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "✅ Your account has been created successfully! "
                "You can now log in using your ID/NEMIS number and password.",
            )
            return redirect("student_login")
        messages.error(request, "❌ Please correct the errors below.")
    else:
        form = VerifiedStudentSignupForm()

    return render(request, "bursary/signup.html", {"form": form})


# ========================
# AJAX verification endpoint
# ========================
@require_POST
def verify_identity_ajax(request):
    """AJAX: Verify ID or NEMIS number."""
    id_type = request.POST.get("id_type", "").strip()
    site_profile = SiteProfile.get_active()
    if not site_profile:
        return JsonResponse({"valid": False, "message": "System not configured."}, status=400)

    county_name = ""
    if site_profile.level == "county" and site_profile.county:
        county_name = site_profile.county.name
    elif site_profile.level == "constituency" and site_profile.constituency and site_profile.constituency.county:
        county_name = site_profile.constituency.county.name

    if id_type == "id":
        id_number = request.POST.get("id_number", "").strip()
        valid, message, _, _ = verify_id(id_number, county_name=county_name)
        return JsonResponse({"valid": valid, "message": message})

    elif id_type == "nemis":
        nemis = request.POST.get("nemis_number", "").strip()
        guardian = request.POST.get("guardian_id_number", "").strip()
        valid, message, _, _ = verify_nemis(nemis, county_name=county_name, guardian_id=guardian)
        return JsonResponse({"valid": valid, "message": message})

    return JsonResponse({"valid": False, "message": "Invalid verification request."}, status=400)


# ========================
# Student Login
# ========================
from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import StudentLoginForm
from .models import Student


def student_login_view(request):
    if request.method == "POST":
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            if user:
                # Ensure there's a Student record associated — show general inline error if missing
                student = Student.objects.filter(user=user).first()
                if student:
                    login(request, user)
                    return redirect("student_dashboard")
                else:
                    form.add_error(None, "Your student record is missing. Please contact support.")
        # If form is valid but user was not set, errors were already attached in form.clean()
    else:
        form = StudentLoginForm()

    return render(request, "bursary/student_login.html", {"form": form})


@login_required
def upgrade_to_id_view(request):
    # ✅ safer fetch: handles case where Student doesn’t exist
    student = getattr(request.user, "student", None)
    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("student_dashboard")

    if request.method == "POST":
        form = UpgradeToIDForm(request.POST, student=student)
        if form.is_valid():
            new_id = form.cleaned_data["id_number"]

            # Update student profile
            student.id_number = new_id
            student.nemis_number = None  # 🚨 retire old NEMIS, prevent duplication/fraud
            student.save(update_fields=["id_number", "nemis_number"])

            # Update user login username
            user = student.user
            user.username = new_id
            user.save(update_fields=["username"])

            messages.success(
                request,
                "✅ Your account has been upgraded. "
                "From now on, you will log in using your National ID only."
            )
            return redirect("student_dashboard")
    else:
        form = UpgradeToIDForm(student=student)

    return render(request, "bursary/upgrade_to_id.html", {"form": form})


# ========================
# Change Password (optional, not forced)
# ========================
@login_required
def change_password(request):
    if request.method == "POST":
        form = SimplePasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep user logged in
            messages.success(request, "✅ Your password was successfully updated!")
            return redirect("student_profile")
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = SimplePasswordChangeForm(user=request.user)

    return render(request, "bursary/change_password.html", {"form": form})


# ========================
# Landing Page View
# ========================

def landing_page(request):
    # ✅ Get branding profile (county or constituency)
    site_profile = SiteProfile.objects.only(
        "id", "bursary_type", "county", "constituency", "application_deadline"
    ).first()

    # ✅ Get landing content
    slides = LandingSlide.objects.filter(is_active=True).order_by("order")
    success_stories = SuccessStory.objects.filter(is_active=True).order_by("order")

    # ✅ Calculate impact stats
    total_students = BursaryApplication.objects.count()
    total_funds = (
        BursaryApplication.objects.aggregate(total=Sum("amount_awarded"))["total"] or 0
    )

    coverage_count, coverage_label = 0, ""

    if site_profile:
        bursary_type = site_profile.bursary_type.lower()

        if bursary_type == "county" and site_profile.county:
            # County-level bursary → count constituencies in this county
            coverage_count = (
                BursaryApplication.objects.filter(
                    constituency__county=site_profile.county
                )
                .values("constituency")
                .distinct()
                .count()
            )
            coverage_label = "📍 Constituencies Covered"

        elif bursary_type == "constituency" and site_profile.constituency:
            # Constituency-level bursary → count wards in this constituency
            coverage_count = (
                BursaryApplication.objects.filter(
                    constituency=site_profile.constituency
                )
                .values("ward")
                .distinct()
                .count()
            )
            coverage_label = "📍 Wards Covered"

    # ✅ Package stats
    stats = {
        "students": total_students,
        "funds": total_funds,
        "coverage": coverage_count,
        "coverage_label": coverage_label,
    }

    # ✅ Render template with everything
    return render(
        request,
        "bursary/landing.html",
        {
            "site_profile": site_profile,
            "slides": slides,
            "success_stories": success_stories,
            "stats": stats,
        },
    )


# ========================
# Officer Dashboard (Application List and Stats)
# ========================
@login_required
def officer_dashboard(request):
    try:
        officer = request.user.officer_profile
    except OfficerProfile.DoesNotExist:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('officer_login')

    # latest activity for ticker (only 1 row fetched)
    recent_activity = OfficerActivityLog.objects.order_by("-timestamp").only("action", "timestamp").first()

    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    ward_filter = request.GET.get('ward', '')

    # ✅ preload related objects, avoid N+1 queries
    applications = (
        BursaryApplication.objects
        .select_related('student', 'constituency', 'ward')
        .filter(bursary_type=officer.bursary_type, constituency=officer.constituency)
    )

    if ward_filter:
        applications = applications.filter(ward_id=ward_filter)

    if status_filter:
        applications = applications.filter(status=status_filter)

    # ✅ compute aggregates efficiently
    aggregate_data = applications.aggregate(
        total_requested=Sum("amount_requested"),
        total_approved=Sum("amount_awarded", filter=Q(status="approved")),
    )
    total_apps = applications.count()
    total_requested = aggregate_data["total_requested"] or 0
    total_approved = aggregate_data["total_approved"] or 0

    # ✅ avoid re-querying for each status
    status_counts = {
        item["status"]: item["count"]
        for item in applications.values("status").annotate(count=Count("id"))
    }

    status_data = {
        "Pending": status_counts.get("pending", 0),
        "Approved": status_counts.get("approved", 0),
        "Rejected": status_counts.get("rejected", 0),
    }

    wards = Ward.objects.filter(constituency=officer.constituency).only("id", "name")

    return render(request, 'bursary/officer_dashboard.html', {
        "officer": officer,
        "recent_activity": recent_activity,
        "applications": applications,  # ⚠️ might need pagination later if too big
        "total_apps": total_apps,
        "total_requested": total_requested,
        "total_approved": total_approved,
        "status_data": status_data,
        "wards": wards,
        "selected_ward": ward_filter,
        "selected_status": status_filter,
        "application_type": officer.bursary_type,
        "chart_labels": json.dumps(list(status_data.keys())),
        "chart_values": json.dumps(list(status_data.values())),
    })


# ========================
# Student Dashboard
# ========================
@login_required
def student_dashboard(request):
    student = Student.objects.filter(user=request.user).select_related("user", "constituency").first()
    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("student_signup")

    application = (
        BursaryApplication.objects
        .filter(student=student)
        .only("status", "amount_requested", "amount_awarded")
        .first()
    )

    if application:
        status_map = {
            "pending": "Your application is still pending.",
            "verified": "Your application has been verified.",
            "approved": "Your application has been approved.",
            "rejected": "Your application has been rejected.",
        }
        application_status = status_map.get(application.status, "Unknown status.")
    else:
        application_status = "You have not submitted any bursary application yet."

    if request.session.pop("show_password_message", False):
        messages.success(request, "Password updated successfully.")

    return render(request, "bursary/student_dashboard.html", {
        "student": student,
        "application": application,
        "application_status": application_status,
    })



# ========================
# Student Profile View
# ========================
@login_required
def student_profile_view(request):
    student = Student.objects.filter(user=request.user).select_related("constituency").first()
    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("student_profile_edit")

    return render(request, "bursary/student_profile_view.html", {"student": student})


# ========================
# Student Profile Edit View
# ========================
@login_required
def student_profile_edit(request):
    student = Student.objects.filter(user=request.user).first()
    if not student:
        messages.error(request, "Student profile not found.")
        return redirect("student_profile_view")

    user = request.user

    if request.method == "POST":
        student_form = StudentProfileForm(request.POST, request.FILES, instance=student)
        user_form = UserForm(request.POST, instance=user)

        if student_form.is_valid() and user_form.is_valid():
            student_form.save()
            user_form.save()
            messages.success(request, "✅ Profile updated successfully.")
            return redirect("student_profile")
    else:
        student_form = StudentProfileForm(instance=student)
        user_form = UserForm(instance=user)

    return render(request, "bursary/student_profile_edit.html", {
        "student_form": student_form,
        "user_form": user_form,
    })


# ========================
# Application Preview View
# ========================
@login_required
def application_preview(request):
    student = Student.objects.filter(user=request.user).first()
    if not student:
        messages.error(request, "Student profile not found. Please update your profile first.")
        return redirect("student_profile_edit")

    application = BursaryApplication.objects.filter(student=student).first()
    if not application:
        messages.error(request, "You have not submitted an application yet.")
        return redirect("apply_bursary")

    if application.status == "rejected":
        messages.info(request, "Your previous application was rejected. You can update it.")
        return redirect("apply_bursary")

    # ✅ preload related data
    guardians = Guardian.objects.filter(student=student)
    siblings = Sibling.objects.filter(student=student)
    supporting_documents = SupportingDocument.objects.filter(application=application)

    return render(request, "bursary/application_preview.html", {
        "student": student,
        "application": application,
        "guardians": guardians,
        "siblings": siblings,
        "supporting_documents": supporting_documents,
    })


# ========================
# Applications Page (List + Filters + Pagination)
# ========================
@login_required
def officer_applications(request):
    applications = (
        BursaryApplication.objects
        .select_related("student", "constituency")
        .defer("feedback")  # ⚡ skip heavy text fields unless needed
    )

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")

    if query:
        applications = applications.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(student__admission_number__icontains=query) |
            Q(student__id_number__icontains=query) |
            Q(student__institution__icontains=query)
        )

    if status:
        applications = applications.filter(status=status)

    paginator = Paginator(applications, 20)  # ✅ paginate to avoid huge loads
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "bursary/officer_applications.html", {
        "applications": page_obj,
        "selected_status": status,
        "search_query": query,
        "page_obj": page_obj,
    })


# ========================
# Export Applications as CSV
# ========================
@login_required
def export_applications_csv(request):
    applications = (
        BursaryApplication.objects
        .select_related("student", "constituency")
        .only(
            "student__first_name", "student__last_name", "student__admission_number", "student__id_number",
            "student__institution", "student__course", "student__year_of_study",
            "student__phone", "student__email",
            "fees_required", "fees_paid", "amount_requested", "amount_awarded",
            "status", "feedback", "constituency__name", "date_applied"
        )
    )

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")

    if query:
        applications = applications.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(student__admission_number__icontains=query) |
            Q(student__id_number__icontains=query) |
            Q(student__institution__icontains=query)
        )

    if status:
        applications = applications.filter(status=status)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = "bursary_applications"
    if status:
        filename += f"_{status}"
    if query:
        filename += "_filtered"
    response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "First Name", "last Name", "Admission No", "ID No", "Institution", "Course", "Year of Study",
        "Constituency", "Fees Required", "Fees Paid", "Amount Requested", "Amount Awarded",
        "Status", "Feedback", "Phone", "Email", "Guardian Name", "Guardian Income", "Submission Date"
    ])

    # ✅ Prefetch guardians to avoid per-row queries
    guardian_map = {
        g.student_id: g for g in Guardian.objects.filter(student__in=[a.student for a in applications])
    }

    for app in applications:
        student = app.student
        guardian = guardian_map.get(student.id)

        writer.writerow([
            student.first_name,
            student.last_name,
            student.admission_number,
            student.id_number,
            student.institution,
            student.course,
            student.year_of_study,
            app.constituency.name if app.constituency else "",
            app.fees_required or 0,
            app.fees_paid or 0,
            app.amount_requested or 0,
            app.amount_awarded or 0,
            app.status.title(),
            app.feedback or "",
            student.phone,
            student.email,
            guardian.name if guardian else "",
            guardian.income if guardian else "",
            app.date_applied.strftime("%Y-%m-%d %H:%M"),
        ])

    return response


# ========================
# Export Applications as PDF
# ========================
@login_required
def export_applications_pdf(request):
    applications = (
        BursaryApplication.objects
        .select_related("student", "constituency")
        .only(
            "student__first_name", "student__last_name", "student__admission_number", "student__institution",
            "student__course", "amount_requested", "amount_awarded", "status", "date_applied"
        )
    )

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")

    if query:
        applications = applications.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(student__admission_number__icontains=query) |
            Q(student__id_number__icontains=query) |
            Q(student__institution__icontains=query)
        )

    if status:
        applications = applications.filter(status=status)

    response = HttpResponse(content_type="application/pdf")
    filename = "bursary_applications"
    if status:
        filename += f"_{status}"
    if query:
        filename += "_filtered"
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Bursary Applications Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    data = [[
        "Full Name", "Admission No", "Institution", "Course",
        "Requested", "Awarded", "Status", "Date"
    ]]

    for app in applications:
        student = app.student
        data.append([
            student.full_name,
            student.admission_number,
            student.institution,
            student.course,
            f"{app.amount_requested or 0}",
            f"{app.amount_awarded or 0}",
            app.status.title(),
            app.date_applied.strftime("%Y-%m-%d"),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#343a40")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    elements.append(table)
    doc.build(elements)

    return response



# ========================
# PDF Utilities
# ========================
def render_to_pdf(template_src, context_dict={}):
    """Render HTML template with context into a PDF response."""
    template = get_template(template_src)
    html = template.render(context_dict)
    result = HttpResponse(content_type="application/pdf")
    pisa_status = pisa.CreatePDF(html, dest=result, link_callback=fetch_resources)

    if pisa_status.err:
        return HttpResponse(f"We had some errors generating the PDF <pre>{html}</pre>")

    return result


def fetch_resources(uri, rel):
    """Convert static/media resource paths for PDF generation."""
    return finders.find(uri)


# ========================
# Student PDF Application
# ========================
@login_required
def application_pdf(request):
    try:
        student = request.user.student
        application = BursaryApplication.objects.get(student=student)
        guardian = Guardian.objects.filter(student=student).first()
        siblings = Sibling.objects.filter(student=student)
        supporting_documents = SupportingDocument.objects.filter(application=application)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("student_profile_edit")
    except BursaryApplication.DoesNotExist:
        messages.error(request, "No application found. Please apply first.")
        return redirect("apply_bursary")

    return render_to_pdf("bursary/pdf_template.html", {
        "student": student,
        "application": application,
        "guardian": guardian,
        "siblings": siblings,
        "supporting_documents": supporting_documents,
    })


# ========================
# Officer Login
# ========================
class OfficerLoginView(LoginView):
    template_name = "bursary/officer_login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        try:
            officer_profile = user.officer_profile
        except OfficerProfile.DoesNotExist:
            messages.error(self.request, "You are not authorized to log in here.")
            return self.form_invalid(form)

        if not officer_profile.is_active:
            messages.error(self.request, "Your officer account is inactive. Contact admin.")
            return self.form_invalid(form)

        login(self.request, user)
        log_officer_action(officer_profile, "login", "Officer logged in")

        return redirect("officer_dashboard")


# ========================
# Officer Profile (View & Edit)
# ========================
@login_required
def officer_profile_view(request):
    """Read-only officer profile page."""
    try:
        officer_profile = request.user.officer_profile
    except OfficerProfile.DoesNotExist:
        messages.error(request, "We couldn't find your officer profile.")
        return redirect("officer_dashboard")

    return render(request, "bursary/officer_profile.html", {"officer": officer_profile})


@login_required
def edit_officer_profile(request):
    """Allow officer to edit their own profile (email, phone, profile pic)."""
    try:
        officer = request.user.officer_profile
    except OfficerProfile.DoesNotExist:
        messages.error(request, "We couldn't find your officer profile.")
        return redirect("officer_dashboard")

    if request.method == "POST":
        form = OfficerSelfProfileForm(
            request.POST, request.FILES,
            instance=officer, user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Profile updated successfully.")
            return redirect("officer_profile")
    else:
        form = OfficerSelfProfileForm(instance=officer, user=request.user)

    return render(request, "bursary/officer_edit_profile.html", {
        "form": form,
        "officer": officer
    })


# ========================
# Application Detail (Officer View)
# ========================
@login_required
def application_detail(request, application_id):
    application = get_object_or_404(BursaryApplication, id=application_id)

    # Officer authorization
    try:
        officer = request.user.officer_profile
        if (application.constituency != officer.constituency or
            application.bursary_type != officer.bursary_type):
            messages.error(request, "You're not allowed to view this application.")
            return redirect("officer_dashboard")
    except OfficerProfile.DoesNotExist:
        messages.error(request, "Access denied.")
        return redirect("officer_login")

    guardians = Guardian.objects.filter(student=application.student)
    siblings = Sibling.objects.filter(student=application.student)
    supporting_documents = SupportingDocument.objects.filter(application=application)

    return render(request, "bursary/officer/application_detail.html", {
        "application": application,
        "guardians": guardians,
        "siblings": siblings,
        "supporting_documents": supporting_documents,
    })


# ========================
# Update Application Status (Officer Action)
# ========================
@require_POST
@login_required
def update_application_status(request, application_id):
    application = get_object_or_404(BursaryApplication, id=application_id)
    new_status = request.POST.get("status")

    if new_status not in ["approved", "rejected"]:
        messages.error(request, "Invalid status.")
        return redirect("officer_dashboard")

    try:
        officer = request.user.officer_profile
    except OfficerProfile.DoesNotExist:
        messages.error(request, "Officer profile not found.")
        return redirect("officer_dashboard")

    # Authorization
    if (application.constituency != officer.constituency or
        application.bursary_type != officer.bursary_type):
        messages.error(request, "Not authorized to update this application.")
        return redirect("officer_dashboard")

    # Update application
    application.status = new_status
    application.feedback = request.POST.get("feedback", "")

    # Handle awarded amount safely
    amount_awarded = request.POST.get("amount_awarded")
    if amount_awarded:
        try:
            application.amount_awarded = Decimal(amount_awarded)
        except (ValueError, InvalidOperation):
            messages.error(request, "Invalid amount format.")
            return redirect("application_detail", application_id=application.id)

    application.save()
    log_officer_action(officer, "change_status", f"Updated application #{application.id} to {new_status}")

    messages.success(request, f"Application #{application.id} marked as {new_status}.")
    return redirect("officer_dashboard")


# ========================
# Admin Login
# ========================
def admin_login_view(request):
    if request.user.is_authenticated:
        return redirect("admin_dashboard")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser:
                login(request, user)
                return redirect("admin_dashboard")
            messages.error(request, "You do not have admin privileges.")
            return redirect("admin_login")
    else:
        form = AuthenticationForm()

    return render(request, "bursary/admin_login.html", {"form": form})


# ========================
# Admin Reports
# ========================
@login_required
def admin_reports(request):
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to view reports.")
        return redirect("admin_login")

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    filtered_apps = BursaryApplication.objects.all()
    if start_date and end_date:
        filtered_apps = filtered_apps.filter(date_applied__range=[start_date, end_date])

    context = {
        "total_applications": BursaryApplication.objects.count(),
        "application_status_counts": BursaryApplication.objects.values("status").annotate(count=Count("status")),
        "bursary_type_counts": BursaryApplication.objects.values("bursary_type").annotate(count=Count("bursary_type")),
        "pending_applications": BursaryApplication.objects.filter(status="pending"),
        "filtered_applications": filtered_apps,
    }

    return render(request, "bursary/admin_reports.html", context)



# ========================
# Student Application PDF
# ========================
@login_required
def application_pdf(request):
    student = get_object_or_404(Student, user=request.user)

    application = (
        BursaryApplication.objects
        .select_related("student")
        .filter(student=student)
        .first()
    )
    if not application:
        messages.error(request, "No bursary application found.")
        return redirect("student_dashboard")

    guardian = Guardian.objects.filter(student=student).first()
    siblings = Sibling.objects.filter(student=student)

    template = get_template("bursary/pdf_template.html")
    html = template.render({
        "student": student,
        "application": application,
        "guardian": guardian,
        "siblings": siblings,
    })

    pdf_file = weasyprint.HTML(string=html).write_pdf()
    return FileResponse(io.BytesIO(pdf_file), content_type="application/pdf", filename="bursary_application.pdf")


# ========================
# Submit Bursary Application
# ========================
@login_required
def submit_bursary_application(request):
    student = getattr(request.user, "student", None)
    if not student:
        messages.error(request, "Invalid student account.")
        return redirect("student_login")

    application, created = BursaryApplication.objects.get_or_create(
        student=student,
        defaults={
            "bursary_type": "constituency",  # TODO: adjust dynamically
            "fees_required": 10000,
            "fees_paid": 0,
            "amount_requested": 10000,
            "status": "pending",
            "date_applied": timezone.now(),
        },
    )

    if not created:
        if application.status != "approved":  # prevent overriding approved
            application.status = "pending"
            application.save(update_fields=["status"])

    return redirect("student_dashboard")


# ========================
# Password Change
# ========================
class StudentPasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    template_name = "bursary/password_change.html"
    success_url = reverse_lazy("student_profile")

    def form_valid(self, form):
        # Clear old messages to avoid stacking
        list(messages.get_messages(self.request))
        messages.success(self.request, "✅ Password updated successfully.")
        return super().form_valid(form)


# ========================
# Manager Decorator
# ========================
def manager_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = getattr(request.user, "officer_profile", None)
        if not profile or not profile.is_manager:
            messages.error(request, "Access denied. Managers only.")
            return redirect("officer_dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ========================
# Delete Student Profile Pic
# ========================
@login_required
def delete_profile_picture(request):
    student = getattr(request.user, "student_profile", None)
    if not student:
        messages.error(request, "Invalid student account.")
        return redirect("student_login")

    if student.profile_pic:
        student.profile_pic.delete(save=False)
        student.profile_pic = None
        student.save(update_fields=["profile_pic"])
        messages.success(request, "Profile picture deleted successfully.")
    else:
        messages.info(request, "No profile picture to delete.")

    return redirect("student_profile")


# ========================
# Officer Management
# ========================
@login_required
@manager_required
def manage_officers(request):
    profile = request.user.officer_profile
    officers = (
        OfficerProfile.objects
        .filter(constituency=profile.constituency, is_active=True)
        .select_related("user", "constituency")
    )
    return render(request, "bursary/manage_officers.html", {"officers": officers})


# Senior officer utility
def is_senior_officer(user):
    return user.groups.filter(name="SeniorOfficer").exists() or user.is_superuser


# ========================
# Add Officer
# ========================
@login_required
@manager_required
def add_officer(request):
    manager_profile = get_object_or_404(OfficerProfile, user=request.user)

    if request.method == "POST":
        user_form = OfficerUserForm(request.POST)
        profile_form = OfficerProfileForm(request.POST, request.FILES)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data["password"])
            user.is_active = True
            user.save()

            officer_profile = profile_form.save(commit=False)
            officer_profile.user = user
            officer_profile.constituency = manager_profile.constituency
            officer_profile.county = getattr(manager_profile.constituency, "county", None)
            officer_profile.bursary_type = manager_profile.bursary_type
            officer_profile.save()

            log_officer_action(manager_profile, "add_officer", f"Added officer {user.username}")
            messages.success(request, f"✅ Officer {user.get_full_name()} added successfully.")
            return redirect("manage_officers")
    else:
        user_form = OfficerUserForm()
        profile_form = OfficerProfileForm()

    return render(
        request,
        "bursary/add_officer.html",
        {"user_form": user_form, "profile_form": profile_form, "manager_profile": manager_profile},
    )


def log_officer_action(officer_profile, action, description=""):
    OfficerActivityLog.objects.create(
        officer=officer_profile,
        action=action,
        description=description,
    )


# ========================
# Edit Officer
# ========================
@login_required
@manager_required
def edit_officer(request, officer_id):
    profile = request.user.officer_profile
    officer = get_object_or_404(OfficerProfile, id=officer_id, constituency=profile.constituency)

    if request.method == "POST":
        user_form = OfficerUserForm(request.POST, instance=officer.user)
        profile_form = OfficerProfileForm(request.POST, request.FILES, instance=officer)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            if user_form.cleaned_data.get("password"):
                user.set_password(user_form.cleaned_data["password"])
            user.save()
            profile_form.save()

            if officer.user == request.user:
                update_session_auth_hash(request, user)

            log_officer_action(profile, "edit_officer", f"Edited officer {user.username}")
            messages.success(request, "Officer updated successfully.")
            return redirect("manage_officers")
    else:
        user_form = OfficerUserForm(instance=officer.user)
        profile_form = OfficerProfileForm(instance=officer)

    return render(request, "bursary/edit_officer.html", {"user_form": user_form, "profile_form": profile_form})


# ========================
# Delete Officer (Soft Delete)
# ========================
@login_required
@manager_required
def delete_officer(request, officer_id):
    profile = request.user.officer_profile
    officer = get_object_or_404(OfficerProfile, id=officer_id, constituency=profile.constituency)

    if request.method == "POST":
        officer.is_active = False
        officer.user.is_active = False
        officer.user.save(update_fields=["is_active"])
        officer.save(update_fields=["is_active"])

        log_officer_action(profile, "delete_officer", f"Soft-deleted officer {officer.user.username}")
        messages.success(request, f"Officer {officer.user.get_full_name()} deactivated successfully.")
        return redirect("manage_officers")

    return render(request, "bursary/confirm_delete.html", {"officer": officer})


# ========================
# Officer Logs
# ========================
@login_required
def officer_logs(request):
    officer = getattr(request.user, "officer_profile", None)
    if not officer:
        messages.error(request, "You are not authorized to view this page.")
        return redirect("officer_login")

    logs = OfficerActivityLog.objects.filter(officer=officer).order_by("-timestamp")
    paginator = Paginator(logs, 10)
    page_number = request.GET.get("page")
    logs_page = paginator.get_page(page_number)

    return render(request, "bursary/officer_logs.html", {"logs": logs_page})


@login_required
def export_officer_logs(request):
    officer = getattr(request.user, "officer_profile", None)
    if not officer:
        messages.error(request, "You are not authorized to export logs.")
        return redirect("officer_login")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="officer_logs.csv"'

    writer = csv.writer(response)
    writer.writerow(["Officer Username", "Action", "Description", "Timestamp"])

    logs = OfficerActivityLog.objects.filter(officer=officer).order_by("-timestamp").select_related("officer__user")
    for log in logs:
        writer.writerow([log.officer.user.username, log.action, log.description, log.timestamp])

    return response


# ========================
# Officer Reports
# ========================
@login_required
def officer_reports(request):
    officer = getattr(request.user, "officer_profile", None)
    if not officer:
        messages.error(request, "You are not authorized to view reports.")
        return redirect("officer_login")

    applications = BursaryApplication.objects.filter(
        bursary_type=officer.bursary_type,
        constituency=officer.constituency,
    )

    # Date filtering
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    if start_date:
        applications = applications.filter(date_applied__gte=parse_date(start_date))
    if end_date:
        applications = applications.filter(date_applied__lte=parse_date(end_date))

    total_apps = applications.count()
    total_requested = applications.aggregate(
        total=Coalesce(Sum("amount_requested"), Value(0, output_field=DecimalField()))
    )["total"]

    total_approved = applications.filter(status="approved").aggregate(
        total=Coalesce(Sum("amount_awarded"), Value(0, output_field=DecimalField()))
    )["total"]

    status_choices = ["pending", "approved", "rejected"]
    chart_labels = [s.capitalize() for s in status_choices]
    chart_values = [applications.filter(status=s).count() for s in status_choices]

    ward_data = applications.values("ward__name").annotate(
        pending=Count("id", filter=Q(status="pending")),
        approved=Count("id", filter=Q(status="approved")),
        rejected=Count("id", filter=Q(status="rejected")),
        total=Count("id"),
        approved_amount=Coalesce(Sum("amount_awarded", filter=Q(status="approved")), Value(0, output_field=DecimalField())),
    ).order_by("ward__name")

    return render(request, "bursary/reports.html", {
        "applications": applications,
        "start_date": start_date,
        "end_date": end_date,
        "total_apps": total_apps,
        "total_requested": total_requested,
        "total_approved": total_approved,
        "chart_labels": json.dumps(chart_labels),
        "chart_values": json.dumps(chart_values),
        "ward_data": ward_data,
    })


# ========================
# Custom Password Reset Views
# ========================
class CustomPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    html_email_template_name = "registration/password_reset_email.html"
    success_url = reverse_lazy("password_reset_done")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_type = self.request.GET.get("user_type")
        if user_type:
            self.request.session["reset_user_type"] = user_type
        context["user_type"] = self.request.session.get("reset_user_type", "student")
        return context


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_type"] = self.request.session.get("reset_user_type", "student")
        return context


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_type"] = self.request.session.get("reset_user_type", "student")
        return context


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_type"] = self.request.session.get("reset_user_type", "student")
        return context


# ========================
# Support Requests (Student)
# ========================
@login_required
def contact_support_view(request):
    if request.method == "POST":
        form = SupportRequestForm(request.POST)
        if form.is_valid():
            support_request = form.save(commit=False)
            student = getattr(request.user, "student", None)
            if not student:
                messages.error(request, "❌ Student profile not found.")
                return redirect("student_dashboard")

            support_request.student = student
            support_request.save()
            messages.success(request, "✅ Your support request has been submitted.")
            return redirect("student_dashboard")
    else:
        form = SupportRequestForm()

    return render(request, "bursary/contact_support.html", {"form": form})


def is_officer(user):
    return hasattr(user, "officer_profile")


@login_required
@user_passes_test(is_officer)
def officer_support_requests_view(request):
    officer_profile = request.user.officer_profile
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if officer_profile.bursary_type == "constituency" and officer_profile.constituency:
        support_requests = SupportRequest.objects.filter(student__constituency=officer_profile.constituency)
    elif officer_profile.bursary_type == "county":
        support_requests = SupportRequest.objects.filter(student__county__isnull=False)
    else:
        support_requests = SupportRequest.objects.none()

    if query:
        support_requests = support_requests.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(student__admission_number__icontains=query)
        )

    if status == "resolved":
        support_requests = support_requests.filter(resolved=True)
    elif status == "unresolved":
        support_requests = support_requests.filter(resolved=False)

    latest_app = BursaryApplication.objects.filter(student=OuterRef("student")).order_by("-date_applied").values("date_applied")[:1]
    support_requests = support_requests.annotate(latest_date_applied=Subquery(latest_app)).order_by("-latest_date_applied")

    unresolved_count = support_requests.filter(resolved=False).count()
    paginator = Paginator(support_requests, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "bursary/officer_support_requests.html", {
        "support_requests": page_obj,
        "unresolved_count": unresolved_count,
        "page_obj": page_obj,
        "query": query,
        "status": status,
    })


@login_required
def officer_support_request_detail(request, pk):
    support_request = get_object_or_404(SupportRequest, pk=pk)
    student = support_request.student
    application = BursaryApplication.objects.filter(student=student).last()

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        if not action:
            messages.error(request, "❌ Officer notes are required before resolving.")
            return redirect("officer_support_request_detail", pk=pk)

        if support_request.resolved:
            support_request.officer_action = action
            support_request.save()
            log_desc = f"Updated support request from {student.user.get_full_name()} ({student.admission_number})"
            messages.success(request, "✏️ Support request updated successfully.")
        else:
            support_request.resolved = True
            support_request.officer_action = action
            support_request.save()

            if "allow_reapply" in request.POST and application:
                application.delete()
                messages.success(request, f"{student.user.username}'s previous application has been deleted. Student can reapply now.")

            log_desc = f"Resolved support request from {student.user.get_full_name()} ({student.admission_number})"
            messages.success(request, "✅ Support request resolved successfully.")

        OfficerActivityLog.objects.create(
            officer=request.user.officer_profile,
            action="resolve_support_request",
            description=log_desc,
        )
        return redirect("officer_support_requests")

    return render(request, "bursary/officer_support_request_detail.html", {
        "support_request": support_request,
        "student": student,
        "application": application,
    })


@login_required
@user_passes_test(is_officer)
def resolve_support_request(request, pk):
    support_request = get_object_or_404(SupportRequest, pk=pk)
    if not support_request.resolved:
        support_request.resolved = True
        support_request.save(update_fields=["resolved"])
        OfficerActivityLog.objects.create(
            officer=request.user.officer_profile,
            action="resolve_support",
            description=f"Resolved support request #{support_request.id} - {support_request.subject}",
        )
        messages.success(request, "Support request marked as resolved and logged.")
    else:
        messages.info(request, "This request is already resolved.")

    return redirect("officer_support_requests")


@login_required
def student_support_requests_view(request):
    student = getattr(request.user, "student_profile", None)
    if not student:
        messages.error(request, "Invalid student account.")
        return redirect("student_dashboard")

    requests = SupportRequest.objects.filter(student=student).order_by("-created_at")
    paginator = Paginator(requests, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "bursary/student_support_requests.html", {
        "student": student,
        "support_requests": page_obj,
        "page_obj": page_obj,
    })


@login_required
def student_support_request_detail(request, pk):
    student = getattr(request.user, "student_profile", None)
    support_request = get_object_or_404(SupportRequest, pk=pk, student=student)

    if support_request.officer_action and not support_request.viewed_by_student:
        support_request.viewed_by_student = True
        support_request.save(update_fields=["viewed_by_student"])

    return render(request, "bursary/student_support_request_detail.html", {"support_request": support_request})


def download_single_application(request, pk):
    """
    Download a single application as CSV.
    """
    try:
        app = BursaryApplication.objects.select_related('student').get(id=pk)
    except BursaryApplication.DoesNotExist:
        raise Http404("Application not found.")

    response = HttpResponse(content_type='text/csv')
    filename = f"{app.student.admission_number}_application.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    # Header
    writer.writerow([
        "First Name", "Last Name", "Admission No", "ID No", "Institution", "Course",
        "Year of Study", "Constituency", "Fees Required", "Fees Paid", "Amount Requested",
        "Amount Awarded", "Status", "Feedback", "Phone", "Email",
        "Guardian Name", "Guardian Income", "Submission Date"
    ])

    student = app.student
    guardians = student.guardians.all()

    # Concatenate guardian names and incomes (comma-separated)
    guardian_names = ", ".join([g.name for g in guardians]) if guardians else ""
    guardian_incomes = ", ".join([str(g.income) for g in guardians]) if guardians else ""

    writer.writerow([
        student.first_name,
        student.last_name,
        student.admission_number,
        student.id_number or student.nemis_number,
        student.institution or '',
        student.course or '',
        student.year_of_study or '',
        getattr(student.constituency, 'name', '') if hasattr(student, 'constituency') else '',
        app.fees_required or '',
        app.fees_paid or '',
        app.amount_requested or '',
        app.amount_awarded or '',
        app.status,
        app.feedback or '',
        student.phone or '',
        student.email or '',
        guardian_names,
        guardian_incomes,
        app.date_applied.strftime("%Y-%m-%d %H:%M") if app.date_applied else ''
    ])

    return response


def download_applications_by_status(request, status):
    """
    Download applications filtered by status as CSV.
    """
    applications = BursaryApplication.objects.select_related('student', 'student__guardian').filter(status=status)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="applications_{status}.csv"'

    writer = csv.writer(response)
    # Header
    writer.writerow([
        "First Name", "Last Name", "Admission No", "ID No", "Institution", "Course",
        "Year of Study", "Constituency", "Fees Required", "Fees Paid", "Amount Requested",
        "Amount Awarded", "Status", "Feedback", "Phone", "Email",
        "Guardian Name", "Guardian Income", "Submission Date"
    ])

    for app in applications:
        student = app.student
        guardian = getattr(student, 'guardian', None)
        writer.writerow([
            student.first_name,
            student.last_name,
            student.admission_number,
            student.id_number or student.nemis_number,
            student.institution or '',
            student.course or '',
            student.year_of_study or '',
            getattr(student.constituency, 'name', '') if hasattr(student, 'constituency') else '',
            app.fees_required or '',
            app.fees_paid or '',
            app.amount_requested or '',
            app.amount_awarded or '',
            app.status,
            app.feedback or '',
            student.phone or '',
            student.email or '',
            guardian.full_name if guardian else '',
            guardian.income if guardian else '',
            app.submission_date.strftime("%Y-%m-%d %H:%M") if app.submission_date else ''
        ])

    return response

