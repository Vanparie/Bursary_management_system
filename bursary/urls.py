from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import (
    signup_view, OfficerLoginView, StudentPasswordChangeView,
    admin_login_view, CustomPasswordResetView,
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView
)
from django.views.generic import TemplateView

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    #path("showcase/", views.LandingContent, name="landing_content"),

    # Student section
    #path('signup/', views.signup_view, name='signup'),
    #path("signup/", views.signup_view, name="signup"),
    path('ajax/verify-identity/', views.verify_identity_ajax, name='verify_identity_ajax'),

    path('student/signup/', signup_view, name='student_signup'),
    path('student/login/', views.student_login_view, name='student_login'),
    #path('verify-login/', views.verify_login, name='verify_login'),
    path('student/logout/', auth_views.LogoutView.as_view(next_page='landing_page'), name='logout'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/apply/', views.apply_bursary, name='apply_bursary'),
    path('student/preview/', views.application_preview, name='application_preview'),
    path('student/profile/', views.student_profile_view, name='student_profile'),
    path('student/profile/edit/', views.student_profile_edit, name='student_profile_edit'),
    path('student/profile/password/', StudentPasswordChangeView.as_view(), name='password_change'),
    path('student/download/pdf/', views.application_pdf, name='application_pdf'),
    path('student/change-password/', views.change_password, name='change_password'),
    #path('change-password/', views.change_password_from_dashboard, name='change_password_dashboard'),
    path('student/profile/delete-picture/', views.delete_profile_picture, name='delete_profile_picture'),
    path('support/', views.contact_support_view, name='contact_support'),
    path('student/support/requests/', views.student_support_requests_view, name='student_support_requests'),
    path("support/request/<int:pk>/", views.student_support_request_detail, name="student_support_request_detail"),


    # Officer panel
    path('officer/dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('officer/update-status/<int:application_id>/', views.update_application_status, name='update_application_status'),
    path('officer/application/<int:application_id>/', views.application_detail, name='application_detail'),
    path('officer/login/', OfficerLoginView.as_view(), name='officer_login'),
    path('officer/profile/', views.officer_profile_view, name='officer_profile'),
    path('officer/manage/', views.manage_officers, name='manage_officers'),
    path('officer/add/', views.add_officer, name='add_officer'),
    path('officer/<int:officer_id>/edit/', views.edit_officer, name='edit_officer'),
    path('officer/<int:officer_id>/delete/', views.delete_officer, name='delete_officer'),
    path('officer/logs/', views.officer_logs, name='officer_logs'),
    path('officer/export-logs/', views.export_officer_logs, name='export_officer_logs'),
    path('officer/export-applications/', views.export_applications_csv, name='export_applications_csv'),
    path('officer/reports/', views.officer_reports, name='officer_reports'),
    path("officer/applications/", views.officer_applications, name="officer_applications"),
    path("officer/export-applications", views.export_applications_pdf, name="export_applications_pdf"),
    path('officer/profile/edit/', views.edit_officer_profile, name='edit_officer_profile'),
    path('officer/password-change/', auth_views.PasswordChangeView.as_view(template_name='bursary/officer_password_change.html', success_url='/officer/password-change/done/'), name='officer_password_change'),
    path('officer/password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='bursary/officer_password_change_done.html'), name='officer_password_change_done'),
    path('officer/support-requests/', views.officer_support_requests_view, name='officer_support_requests'),
    path('officer/support-request/<int:pk>/', views.officer_support_request_detail, name='officer_support_request_detail'),
    path('support-requests/<int:pk>/resolve/', views.resolve_support_request, name='resolve_support_request'),
    path('officer/applications/download/status/<str:status>/', views.download_applications_by_status, name='download_applications_by_status'),
    path('officer/application/<int:pk>/download/', views.download_single_application, name='download_single_application'),


    # Admin section
    #path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/reports/', views.admin_reports, name='admin_reports'),
    path('admin/login/', admin_login_view, name='admin_login'),

    # Password Reset Flow
    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),


    # === Legal / Compliance pages ===
    path('privacy/', TemplateView.as_view(template_name="bursary/privacy.html"), name="privacy"),
    path('terms/', TemplateView.as_view(template_name="bursary/terms.html"), name="terms"),

]