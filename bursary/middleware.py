from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from bursary.models import SiteProfile


EXEMPT_PATHS = [
    "/no-access/",
    "/student_no-access/",
]


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _is_exempt_path(self, request):
        path = request.path
        return (
            any(path.startswith(p) for p in EXEMPT_PATHS)
            or path.startswith(settings.STATIC_URL)
            or path.startswith(settings.MEDIA_URL)
        )

    def _get_subdomain(self, request):
        host = request.get_host().split(":")[0]
        parts = host.split(".")

        if len(parts) < 3:
            return None

        return parts[0].lower()

    def __call__(self, request):
        subdomain = self._get_subdomain(request)

        # Try subdomain first
        site_profile = None
        if subdomain:
            site_profile = SiteProfile.objects.filter(
                slug=subdomain,
                is_active=True
            ).first()

        # ✅ Fallback to active site (IMPORTANT FIX)
        if not site_profile:
            site_profile = SiteProfile.objects.filter(is_active=True).first()

        request.site_profile = site_profile

        # Still nothing → system misconfigured
        if not site_profile:
            return self.get_response(request)

        # Allow public paths
        if self._is_exempt_path(request):
            return self.get_response(request)

        user = getattr(request, "user", None)

        if user and user.is_authenticated:

            if user.is_superuser or user.is_staff:
                return self.get_response(request)

            officer = getattr(user, "officer_profile", None)
            if officer and officer.site_profile_id != site_profile.id:
                return redirect(getattr(settings, "NO_ACCESS_URL", "/no-access/"))

            student = getattr(user, "student", None)
            if student and student.site_profile_id != site_profile.id:
                return redirect(getattr(settings, "NO_ACCESS_URL", "/student_no-access/"))

        return self.get_response(request)