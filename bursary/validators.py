import os
from django.conf import settings
from django.core.exceptions import ValidationError

# Allowed file extensions (simple whitelist)
ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png']


def validate_file_extension(value):
    """
    Validate file extension against allowed list.
    """
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type: {ext}. Allowed types are: PDF, JPG, JPEG, PNG."
        )


def validate_file_size(value):
    """
    Enforce maximum file size.
    Default: 2 MB unless overridden in settings.py with MAX_UPLOAD_SIZE.
    """
    max_size = getattr(settings, "MAX_UPLOAD_SIZE", 2 * 1024 * 1024)  # 2 MB default
    if value.size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise ValidationError(
            f"File size exceeds the {max_mb} MB limit."
        )


