# bursary/auth_backends.py

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q


class StudentIDorNEMISBackend(ModelBackend):
    """
    Custom backend to allow ONLY students to log in using:
    - National ID (Student.id_number)
    - NEMIS Number (Student.nemis_number)
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Look for a User linked to a Student profile
            user = User.objects.filter(
                Q(student_profile__id_number=username) |
                Q(student_profile__nemis_number=username)
            ).distinct().first()

            # Ensure user exists, password matches, and they have a student_profile
            if user and user.check_password(password) and hasattr(user, "student_profile"):
                return user
        except User.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None



