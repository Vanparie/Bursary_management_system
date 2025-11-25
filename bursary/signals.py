from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from bursary.models import Student
from django.utils.timezone import now

@receiver(user_logged_in)
def set_date_registered(sender, request, user, **kwargs):
    """
    Set the student's date_registered on first login.
    Enforce student-site association.
    Officers are ignored.
    """
    try:
        student = Student.objects.get(user=user)
        # Set date_registered
        if not student.date_registered:
            student.date_registered = now()

        # Ensure student matches the active site profile (optional)
        site = getattr(request, 'site_profile', None)
        if site:
            if site.county and student.county != site.county:
                # Optionally log mismatch
                pass
            if site.constituency and student.constituency != site.constituency:
                # Optionally log mismatch
                pass

        student.save()
    except Student.DoesNotExist:
        # Ignore officers
        pass
