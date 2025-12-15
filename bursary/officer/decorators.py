from django.core.exceptions import PermissionDenied

def officer_required_can_manage_content(view_func):
    def wrapper(request, *args, **kwargs):
        officer = getattr(request.user, "officer_profile", None)

        # Block if no officer OR officer cannot manage content
        if not officer or not officer.can_manage_content:
            raise PermissionDenied("You do not have permission to manage content.")

        return view_func(request, *args, **kwargs)
    return wrapper


def manager_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not getattr(request.user, "officer_profile", None) or not request.user.officer_profile.is_manager:
            raise PermissionDenied("Manager access required.")
        return view_func(request, *args, **kwargs)
    return wrapper

def officer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not getattr(request.user, "officer_profile", None):
            raise PermissionDenied("Officer access required.")
        return view_func(request, *args, **kwargs)
    return wrapper
