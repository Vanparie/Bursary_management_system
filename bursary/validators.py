import os
from django.core.exceptions import ValidationError

def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1].lower()  # Get file extension
    allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
    if ext not in allowed_extensions:
        raise ValidationError(f"Unsupported file type: {ext}. Allowed: PDF, JPG, PNG.")

def validate_file_size(value):
    max_size = 2 * 1024 * 1024  # 2MB
    if value.size > max_size:
        raise ValidationError("File size exceeds 2MB limit.")
