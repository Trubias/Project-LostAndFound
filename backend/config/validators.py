from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


MAX_IMAGE_UPLOAD_SIZE = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}


def validate_image_upload(uploaded_file):
    """Validate image size and decoded format; filenames are not trusted."""
    if uploaded_file.size > MAX_IMAGE_UPLOAD_SIZE:
        raise ValidationError('Image files must be 5 MiB or smaller.')

    try:
        image = Image.open(uploaded_file)
        if image.format not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError('Upload a JPEG, PNG, or WebP image.')
        width, height = image.size
        if width * height > MAX_IMAGE_PIXELS:
            raise ValidationError('Image dimensions are too large.')
        image.verify()
    except ValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ValidationError('Upload a valid JPEG, PNG, or WebP image.')
    finally:
        if hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)
