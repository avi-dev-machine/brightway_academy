from io import BytesIO

import pytest
from PIL import Image

from app.exceptions import FileValidationError
from app.utils.file_validation import read_upload_limited, validate_csv_upload, validate_image
from tests.factories import image_bytes


def error_code(callable_, *args):
    with pytest.raises(FileValidationError) as info:
        callable_(*args)
    return info.value.code


def test_valid_jpeg_is_reencoded():
    result = validate_image(image_bytes("JPEG", (2000, 2600)), "photo.JPG", "image/jpeg")
    assert result.content_type == "image/jpeg"
    with Image.open(BytesIO(result.data)) as image:
        assert image.format == "JPEG"
        assert max(image.size) <= 1200


def test_png_with_transparency_is_flattened():
    result = validate_image(image_bytes("PNG", mode="RGBA"), "photo.png", "image/png")
    with Image.open(BytesIO(result.data)) as image:
        assert image.mode == "RGB"


def test_appended_payload_is_stripped():
    data = image_bytes("JPEG") + b"<?php system($_GET['c']); ?>"
    result = validate_image(data, "photo.jpg", "image/jpeg")
    assert b"<?php" not in result.data


@pytest.mark.parametrize(
    ("data", "filename", "content_type", "code"),
    [
        (image_bytes("JPEG"), "photo.png", "image/jpeg", "EXTENSION_MISMATCH"),
        (image_bytes("JPEG"), "photo.jpg", "image/png", "CONTENT_TYPE_MISMATCH"),
        (image_bytes("JPEG"), "photo.jpg", "application/octet-stream", "CONTENT_TYPE_MISMATCH"),
        (image_bytes("GIF"), "photo.gif", "image/gif", "UNSUPPORTED_IMAGE_TYPE"),
        (image_bytes("JPEG", (50, 50)), "photo.jpg", "image/jpeg", "INVALID_IMAGE_DIMENSIONS"),
        (b"definitely not an image", "photo.jpg", "image/jpeg", "INVALID_IMAGE"),
        (image_bytes("JPEG")[:200], "photo.jpg", "image/jpeg", "INVALID_IMAGE"),
    ],
)
def test_invalid_images(data, filename, content_type, code):
    assert error_code(validate_image, data, filename, content_type) == code


def test_upload_size_limits():
    assert error_code(read_upload_limited, BytesIO(b"x" * 11), 10) == "FILE_TOO_LARGE"
    assert error_code(read_upload_limited, BytesIO(b""), 10) == "FILE_EMPTY"
    assert read_upload_limited(BytesIO(b"abc"), 10) == b"abc"


def test_csv_upload_validation():
    validate_csv_upload("students.csv", "text/csv", b"a,b")
    validate_csv_upload("students.CSV", "application/vnd.ms-excel", b"a,b")
    assert (
        error_code(validate_csv_upload, "students.xlsx", "text/csv", b"a")
        == "INVALID_FILE_EXTENSION"
    )
    assert error_code(validate_csv_upload, "s.csv", "image/png", b"a") == "CONTENT_TYPE_MISMATCH"
    assert error_code(validate_csv_upload, "s.csv", "text/csv", b"a\x00b") == "BINARY_FILE"
