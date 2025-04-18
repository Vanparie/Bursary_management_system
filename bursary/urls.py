from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import signup_view, StaffLoginView

urlpatterns = [
    path('', views.landing_page, name='landing_page'),

    # Student section
    path('student/signup/', signup_view, name='student_signup'),
    path('student/login/', views.student_login_view, name='student_login'),
    path('student/logout/', auth_views.LogoutView.as_view(next_page='landing_page'), name='logout'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/apply/', views.apply_bursary, name='apply_bursary'),
    path('student/preview/', views.application_preview, name='application_preview'),
    path('student/profile/', views.student_profile_view, name='student_profile'),
    path('student/profile/edit/', views.student_profile_edit, name='student_profile_edit'),
    path('student/profile/password/', auth_views.PasswordChangeView.as_view(
        template_name='bursary/password_change.html',
        success_url='/student/profile/'
    ), name='change_password'),
    path('student/download/pdf/', views.application_pdf, name='application_pdf'),

    # Officer panel
    #path('officer/login/', views.officer_login_view, name='officer_login'),
    path('officer/dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('officer/update-status/<int:application_id>/', views.update_application_status, name='update_application_status'),
    path('officer/application/<int:application_id>/', views.application_detail, name='application_detail'),
    path('staff/login/', StaffLoginView.as_view(), name='staff_login'),
    path('officer/profile/', views.officer_profile_view, name='officer_profile'),


    # Admin section
    path('admin/login/', views.admin_login_view, name='admin_login'),  # if custom login required
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/export/', views.export_applications_csv, name='export_applications_csv'),
    path('admin/reports/', views.admin_reports, name='admin_reports'),

    # Password Reset (shared)
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='bursary/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='bursary/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='bursary/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='bursary/password_reset_complete.html'), name='password_reset_complete'),
]
