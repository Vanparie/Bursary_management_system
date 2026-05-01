from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from bursary.models import SiteProfile


EXEMPT_PATHS = [
    "/no-access/",
    "/student_no-access/",
]


class TenantMiddleware:
    """
    Multi-tenant middleware using subdomain (slug-based routing).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _is_exempt_path(self, request):
        path = request.path

        if any(path.startswith(p) for p in EXEMPT_PATHS):
            return True

        if path.startswith(settings.STATIC_URL) or path.startswith(settings.MEDIA_URL):
            return True

        return False

    def _get_subdomain(self, request):
        host = request.get_host().split(":")[0]  # remove port

        # Example:
        # kisumu.bursaryflow.com → ['kisumu', 'bursaryflow', 'com']
        parts = host.split(".")

        if len(parts) < 3:
            return None  # root domain

        return parts[0].lower()

    def __call__(self, request):
        user = getattr(request, "user", None)

        subdomain = self._get_subdomain(request)

        # 🔹 1. Resolve SiteProfile from subdomain
        site_profile = None

        if subdomain:
            site_profile = SiteProfile.objects.filter(
                slug=subdomain,
                is_active=True
            ).first()

        # 🔹 2. Fallback (root domain)
        if not site_profile:
            site_profile = SiteProfile.get_active()

        request.site_profile = site_profile

        #  No site configured at all
        if site_profile is None:
            return self.get_response(request)

        # Allow static/admin/etc
        if self._is_exempt_path(request):
            return self.get_response(request)

        #  3. SECURITY ENFORCEMENT
        if user and user.is_authenticated:

            # Superuser bypass
            if user.is_superuser or user.is_staff:
                return self.get_response(request)

            # Officer validation
            officer = getattr(user, "officer_profile", None)
            if officer:
                if officer.site_profile_id != site_profile.id:
                    return redirect(getattr(settings, "NO_ACCESS_URL", "/no-access/"))

            # Student validation
            student = getattr(user, "student", None)
            if student:
                if student.site_profile_id != site_profile.id:
                    return redirect(getattr(settings, "NO_ACCESS_URL", "/student_no-access/"))

        return self.get_response(request)

