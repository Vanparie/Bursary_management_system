from .models import SiteProfile

def site_branding(request):
    try:
        branding = SiteProfile.objects.first()
    except:
        branding = None
    return {
        'branding': branding
    }
