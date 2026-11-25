import io
from pathlib import Path
from datetime import datetime, timezone
import numpy as np

from PIL import Image, UnidentifiedImageError

from inference import predict_leaf


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MIN_IMAGE_WIDTH = 80
MIN_IMAGE_HEIGHT = 80
MIN_SUPPORTED_LEAF_CONFIDENCE_PERCENT = 20.0
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP"}


class ImageValidationError(ValueError):
    pass


class UnsupportedImageError(ImageValidationError):
    pass


class PredictionServiceError(RuntimeError):
    pass


def validate_upload(file_storage):
    filename = file_storage.filename or ""
    extension = Path(filename).suffix.lower().lstrip(".")

    if extension not in ALLOWED_EXTENSIONS:
        raise ImageValidationError("Please upload JPG, JPEG, PNG or WEBP.")

    contents = file_storage.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise ImageValidationError("Image is too large. Maximum size is 10 MB.")

    if not contents:
        raise ImageValidationError("No image selected.")

    try:
        with Image.open(io.BytesIO(contents)) as source:
            source.verify()
    except (UnidentifiedImageError, OSError):
        raise ImageValidationError("The file is not a valid or supported image.")

    try:
        with Image.open(io.BytesIO(contents)) as source:
            if source.format not in ALLOWED_PIL_FORMATS:
                raise ImageValidationError("Please upload JPG, JPEG, PNG or WEBP.")

            if source.width < MIN_IMAGE_WIDTH or source.height < MIN_IMAGE_HEIGHT:
                raise ImageValidationError(
                    "Image is too small. Please use a clearer photo."
                )

            image = source.convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise ImageValidationError("The file is not a valid or supported image.")

    return image


def analyze_upload(file_storage):
    image = validate_upload(file_storage)
    try:
        result = predict_leaf(image)
    except Exception as error:
        raise PredictionServiceError(
            "The AI model could not process this image. Please try again."
        ) from error

    if result["confidence"] < MIN_SUPPORTED_LEAF_CONFIDENCE_PERCENT:
        raise UnsupportedImageError(
            "I couldn't confidently identify a supported plant leaf. "
            "Please upload a clear, close-up photo of one leaf."
        )

    quality = assess_image_quality(image)
    result["image_quality"] = quality
    result["scan_date"] = datetime.now(timezone.utc).isoformat()
    if quality["status"] != "good":
        result["status"] = "Inconclusive — image quality needs review"
        result["confidence_warning"] = True
    return result


def assess_image_quality(image):
    sample = image.convert("L").resize((224, 224))
    pixels = np.asarray(sample, dtype=np.float32)
    gx = np.diff(pixels, axis=1)
    gy = np.diff(pixels, axis=0)
    edge_strength = float(np.mean(np.abs(gx)) + np.mean(np.abs(gy)))

    if edge_strength < 3.0:
        return {
            "status": "poor",
            "label": "Possible blur or very low detail",
            "message": "Retake the photo in sharper focus with one leaf clearly visible."
        }
    if edge_strength < 7.0:
        return {
            "status": "fair",
            "label": "Image quality could be improved",
            "message": "Use brighter, more evenly lit conditions and avoid motion blur."
        }
    return {
        "status": "good",
        "label": "Image detail appears usable",
        "message": "This is a basic quality check, not a verification that the image contains a leaf."
    }
