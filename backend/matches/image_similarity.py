"""Small, dependency-light perceptual image comparison for report suggestions."""
from PIL import Image, ImageOps


def perceptual_hash(image_file):
    """Return an average hash for an image field/upload, or None if unreadable."""
    try:
        image_file.open('rb')
        with Image.open(image_file) as source:
            image = ImageOps.exif_transpose(source).convert('L').resize((8, 8), Image.Resampling.LANCZOS)
            pixels = list(image.getdata())
        average = sum(pixels) / len(pixels)
        return tuple(pixel >= average for pixel in pixels)
    except (OSError, ValueError, AttributeError):
        return None
    finally:
        try:
            image_file.close()
        except (OSError, AttributeError):
            pass


def image_similarity(image_a, image_b):
    """Return perceptual similarity from 0–100; only a visual hint, not identity proof."""
    hash_a = perceptual_hash(image_a)
    hash_b = perceptual_hash(image_b)
    if hash_a is None or hash_b is None:
        return 0
    distance = sum(bit_a != bit_b for bit_a, bit_b in zip(hash_a, hash_b))
    return round((1 - distance / len(hash_a)) * 100)
