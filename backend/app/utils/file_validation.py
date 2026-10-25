"""Upload validation for photos and CSV files."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.exceptions import FileValidationError

# Refuse decompression bombs well before Pillow's own (warning-only) threshold.
Image.MAX_IMAGE_PIXELS = 40_000_000

_IMAGE_FORMATS: dict[str, tuple[set[str], set[str]]] = {
    # Pillow format -> (allowed extensions, accepted declared MIME types)
    "JPEG": ({".jpg", ".jpeg"}, {"image/jpeg", "image/jpg", "image/pjpeg"}),
    "PNG": ({".png"}, {"image/png"}),
    "WEBP": ({".webp"}, {"image/webp"}),
}
MIN_IMAGE_SIDE = 100
MAX_IMAGE_SIDE = 8000
STORED_IMAGE_MAX_SIDE = 1200

_CSV_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "text/plain",
    "application/vnd.ms-excel",
    "application/octet-stream",
}


@dataclass(frozen=True)
class ValidatedImage:
    data: bytes  # re-encoded JPEG
    width: int
    height: int
    content_type: str = "image/jpeg"


def read_upload_limited(stream: BinaryIO, max_bytes: int) -> bytes:
    data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise FileValidationError(
            f"File is too large (maximum {max_bytes // (1024 * 1024)} MB).", code="FILE_TOO_LARGE"
        )
    if not data:
        raise FileValidationError("The uploaded file is empty.", code="FILE_EMPTY")
    return data


def _extension(filename: str | None) -> str:
    return PurePath(filename or "").suffix.lower()


def _base_type(content_type: str | None) -> str:
    return (content_type or "").split(";")[0].strip().lower()


def validate_image(data: bytes, filename: str | None, content_type: str | None) -> ValidatedImage:
    """Check type, extension, declared MIME, dimensions and integrity, then re-encode.

    Re-encoding to JPEG strips EXIF/GPS metadata and anything appended to the file.
    """
    try:
        with Image.open(BytesIO(data)) as probe:
            image_format = probe.format or ""
            probe.verify()
        with Image.open(BytesIO(data)) as source:
            source.load()
            image = ImageOps.exif_transpose(source)
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombError,
    ) as exc:
        raise FileValidationError(
            "The file is not a valid or supported image.", code="INVALID_IMAGE"
        ) from exc

    if image_format not in _IMAGE_FORMATS:
        raise FileValidationError(
            "Only JPEG, PNG or WebP images are allowed.", code="UNSUPPORTED_IMAGE_TYPE"
        )
    extensions, mime_types = _IMAGE_FORMATS[image_format]
    if _extension(filename) not in extensions:
        raise FileValidationError(
            "The file extension does not match the image content.", code="EXTENSION_MISMATCH"
        )
    if _base_type(content_type) not in mime_types:
        raise FileValidationError(
            "The declared file type does not match the image content.",
            code="CONTENT_TYPE_MISMATCH",
        )
    width, height = image.size
    if min(width, height) < MIN_IMAGE_SIDE or max(width, height) > MAX_IMAGE_SIDE:
        raise FileValidationError(
            f"Image dimensions must be between {MIN_IMAGE_SIDE} and {MAX_IMAGE_SIDE} pixels.",
            code="INVALID_IMAGE_DIMENSIONS",
        )

    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")
    image.thumbnail((STORED_IMAGE_MAX_SIDE, STORED_IMAGE_MAX_SIDE))
    output = BytesIO()
    image.save(output, format="JPEG", quality=88, optimize=True)
    return ValidatedImage(output.getvalue(), width, height)


def validate_csv_upload(filename: str | None, content_type: str | None, data: bytes) -> None:
    if _extension(filename) != ".csv":
        raise FileValidationError("Only .csv files are accepted.", code="INVALID_FILE_EXTENSION")
    if content_type and _base_type(content_type) not in _CSV_CONTENT_TYPES:
        raise FileValidationError("The file is not a CSV file.", code="CONTENT_TYPE_MISMATCH")
    if b"\x00" in data:
        raise FileValidationError("The file appears to be binary, not CSV.", code="BINARY_FILE")
