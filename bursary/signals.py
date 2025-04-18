from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from bursary.models import OfficerProfile, StudentProfile

@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    if created:
        # Avoid creating profile for officers
        is_officer = OfficerProfile.objects.filter(user=instance).exists()
        if not is_officer:
            StudentProfile.objects.create(user=instance)
