from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from bursary.models import Student
from django.utils.timezone import now


@receiver(user_logged_in)
def set_date_registered(sender, request, user, **kwargs):
    """
    Set the student's date_registered on their first login.
    Officers are ignored.
    """
    try:
        student = Student.objects.get(user=user)
        if not student.date_registered:
            student.date_registered = now()
            student.save()
    except Student.DoesNotExist:
        # Ignore if it's an officer or missing student record
        pass

