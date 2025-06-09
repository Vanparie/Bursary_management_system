from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from bursary.models import OfficerProfile, StudentProfile, Student
from django.contrib.auth.signals import user_logged_in
from django.utils.timezone import now

@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    if created:
        # Avoid creating profile for officers
        is_officer = OfficerProfile.objects.filter(user=instance).exists()
        if not is_officer:
            StudentProfile.objects.create(user=instance)


@receiver(user_logged_in)
def set_date_registered(sender, request, user, **kwargs):
    try:
        student = Student.objects.get(user=user)
        if not student.date_registered:
            student.date_registered = now()
            student.save()
    except Student.DoesNotExist:
        pass