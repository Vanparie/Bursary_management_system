from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import signup_view, StaffLoginView, StudentPasswordChangeView

urlpatterns = [
    path('', views.landing_page, name='landing_page'),

    # Student section
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



    # Officer panel
    path('officer/dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('officer/update-status/<int:application_id>/', views.update_application_status, name='update_application_status'),
    path('officer/application/<int:application_id>/', views.application_detail, name='application_detail'),
    path('staff/login/', StaffLoginView.as_view(), name='staff_login'),
    path('officer/profile/', views.officer_profile_view, name='officer_profile'),
    path('officer/manage/', views.manage_officers, name='manage_officers'),
    path('officer/add/', views.add_officer, name='add_officer'),
    path('officer/<int:officer_id>/edit/', views.edit_officer, name='edit_officer'),
    path('officer/<int:officer_id>/delete/', views.delete_officer, name='delete_officer'),
    path('officer/logs/', views.officer_logs, name='officer_logs'),
    path('officer/export-logs/', views.export_officer_logs, name='export_officer_logs'),
    path('officer/export-applications/', views.export_applications_csv, name='export_applications_csv'),
    path('officer/reports/', views.officer_reports, name='officer_reports'),


    # Admin section
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/reports/', views.admin_reports, name='admin_reports'),

    # Password Reset (shared)
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='bursary/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='bursary/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='bursary/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='bursary/password_reset_complete.html'), name='password_reset_complete'),
]
