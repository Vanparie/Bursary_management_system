from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from bursary.models import SiteProfile 
from officers.models import OfficerProfile  
from students.models import Student  

EXEMPT_PATHS = [
    reverse("admin:index"),  # admin UI
    getattr(settings, "NO_ACCESS_URL", "/no-access/"),
    # add other exempt paths here
]

class ActiveSiteProfileMiddleware:
    """
    1. Attach active SiteProfile as request.site_profile
    2. If user is authenticated and is an officer/student, ensure their site_profile matches
       the active one. If not, redirect to a 'no access' page.
    3. Superusers and Django admin paths are exempt.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _is_exempt_path(self, request):
        path = request.path
        for p in EXEMPT_PATHS:
            if path.startswith(p):
                return True
        # allow static/media
        if path.startswith(settings.STATIC_URL) or path.startswith(settings.MEDIA_URL):
            return True
        return False

    def __call__(self, request):
        # Attach active site profile
        request.site_profile = SiteProfile.get_active()

        # If path is exempt, skip access enforcement
        if self._is_exempt_path(request):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            # allow staff and superusers to bypass
            if user.is_staff or user.is_superuser:
                return self.get_response(request)

            # Officer check
            officer = getattr(user, "officer_profile", None)
            if officer:
                # If officer.site_profile exists and doesn't match active, block
                active = request.site_profile
                if active and officer.site_profile != active:
                    return redirect(getattr(settings, "NO_ACCESS_URL", "/no-access/"))

            # Student check
            student = getattr(user, "student", None)
            if student:
                active = request.site_profile
                if active and student.site_profile != active:
                    return redirect(getattr(settings, "NO_ACCESS_URL", "/no-access/"))

        return self.get_response(request)
