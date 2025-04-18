from django.core.mail import send_mail
from django.conf import settings

def send_application_email(student, application):
    subject = "Bursary Application Submitted"
    message = f"""
Dear {student.full_name},

Your bursary application has been successfully received.

Application Details:
- Admission No: {student.admission_number}
- Institution: {student.institution}
- Amount Requested: KES {application.amount_requested}
- Submission Date: {application.date_applied.strftime('%Y-%m-%d %H:%M')}

You will be notified once your application has been reviewed.

Regards,
Bursary Committee - {settings.DEFAULT_FROM_EMAIL}
    """

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [student.email],
        fail_silently=False,
    )
