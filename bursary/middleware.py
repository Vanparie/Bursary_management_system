from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from bursary.models import SiteProfile 
from .models import OfficerProfile  
from .models import Student  

EXEMPT_PATHS = [
    reverse("admin:index"),  # admin UI
    getattr(settings, "NO_ACCESS_URL", "/no-access/"),
    # add other exempt paths here
]

class ActiveSiteProfileMiddleware:
    """
    Attach the user's assigned SiteProfile as request.site_profile.
    Strictly enforce access based on user's assigned site.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _is_exempt_path(self, request):
        path = request.path
        for p in EXEMPT_PATHS:
            if path.startswith(p):
                return True
        if path.startswith(settings.STATIC_URL) or path.startswith(settings.MEDIA_URL):
            return True
        return False

    def __call__(self, request):
        user = getattr(request, "user", None)

        # Determine the site profile based on user assignment
        site_profile = None
        if user and user.is_authenticated:
            if hasattr(user, "officer_profile"):
                site_profile = user.officer_profile.site_profile
            elif hasattr(user, "student"):
                site_profile = user.student.site_profile

        # Fallback for anonymous users or superusers
        if not site_profile:
            site_profile = SiteProfile.get_active()

        request.site_profile = site_profile

        if self._is_exempt_path(request):
            return self.get_response(request)

        # Enforce strict site access
        if user and user.is_authenticated:
            if user.is_superuser or user.is_staff:
                return self.get_response(request)

            # Officer enforcement
            officer = getattr(user, "officer_profile", None)
            if officer and officer.site_profile != site_profile:
                return redirect(getattr(settings, "NO_ACCESS_URL", "/no-access/"))

            # Student enforcement
            student = getattr(user, "student", None)
            if student and student.site_profile != site_profile:
                return redirect(getattr(settings, "NO_ACCESS_URL", "/no-access/"))

        return self.get_response(request)

