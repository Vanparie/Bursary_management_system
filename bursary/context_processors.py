# bursary/context_processors.py
from django.core.cache import cache
from .models import SiteProfile, SupportRequest, Student
import logging

logger = logging.getLogger(__name__)


def site_branding(request):
    """
    Injects active site branding (name + logo) into all templates.
    Caches result for 5 minutes.
    """
    try:
        branding = cache.get("active_branding")
        if not branding:
            site = (
                SiteProfile.objects.only("id", "branding_name", "branding_logo", "is_active")
                .filter(is_active=True)
                .first()
                or SiteProfile.objects.only("id", "branding_name", "branding_logo").first()
            )
            branding = {
                "name": site.branding_name if site else "BursaryFlow",
                "logo": site.branding_logo.url if site and site.branding_logo else None,
            }
            cache.set("active_branding", branding, 300)
        return {"branding": branding}
    except Exception as e:
        logger.error(f"Error in site_branding context processor: {e}")
        return {"branding": {"name": "BursaryFlow", "logo": None}}


def officer_context(request):
    """
    Injects officer profile if available.
    """
    try:
        officer = getattr(request.user, "officer_profile", None) if request.user.is_authenticated else None
        return {"officer": officer}
    except Exception as e:
        logger.error(f"Error in officer_context context processor: {e}")
        return {"officer": None}


def unresolved_support_count(request):
    """
    Adds unresolved support request count for officer dashboards.
    """
    try:
        if request.user.is_authenticated and hasattr(request.user, "officer_profile"):
            officer = request.user.officer_profile

            site = None
            if officer.constituency:
                site = SiteProfile.objects.filter(constituency=officer.constituency).only("id").first()
            elif officer.bursary_type == "county" and officer.constituency:
                site = SiteProfile.objects.filter(county=officer.constituency.county).only("id").first()

            if site:
                filters = {"resolved": False}
                if site.constituency:
                    filters["student__constituency"] = site.constituency
                elif site.county:
                    filters["student__county"] = site.county

                count = SupportRequest.objects.filter(**filters).only("id").count()
                return {"unresolved_support_count": count}

        return {"unresolved_support_count": 0}
    except Exception as e:
        logger.error(f"Error in unresolved_support_count context processor: {e}")
        return {"unresolved_support_count": 0}


def student_support_feedback_count(request):
    """
    Adds unread student support feedback count for logged-in students.
    """
    try:
        if request.user.is_authenticated and not request.user.is_staff:
            student = Student.objects.filter(user=request.user).only("id").first()
            if student:
                count = SupportRequest.objects.filter(
                    student=student,
                    officer_action__isnull=False,
                    viewed_by_student=False
                ).only("id").count()
                return {"student_support_feedback_count": count}
        return {"student_support_feedback_count": 0}
    except Exception as e:
        logger.error(f"Error in student_support_feedback_count context processor: {e}")
        return {"student_support_feedback_count": 0}



