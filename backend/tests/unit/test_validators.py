import pytest
from pydantic import ValidationError

from app.config import Settings
from app.logging import redact
from app.utils.pdf import format_inr
from app.utils.validators import (
    escape_like,
    normalize_indian_phone,
    normalize_whitespace,
    sanitize_csv_cell,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9876543210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("09876543210", "+919876543210"),
        ("919876543210", "+919876543210"),
        ("98765-43210 / 9123456789", "+919876543210"),
        ("033 2456 7890", None),  # landline
        ("12345", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_indian_phone(raw, expected):
    assert normalize_indian_phone(raw) == expected


def test_normalize_whitespace():
    assert normalize_whitespace("  Asha   Roy \n") == "Asha Roy"
    assert normalize_whitespace("   ") is None


def test_escape_like():
    assert escape_like("50%_off\\") == "50\\%\\_off\\\\"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=HYPERLINK(1)", "'=HYPERLINK(1)"),
        ("+1", "'+1"),
        ("@x", "'@x"),
        ("Asha", "Asha"),
        (None, ""),
    ],
)
def test_sanitize_csv_cell(value, expected):
    assert sanitize_csv_cell(value) == expected


@pytest.mark.parametrize(
    ("paise", "expected"),
    [
        (0, "Rs. 0.00"),
        (150, "Rs. 1.50"),
        (12_345_678, "Rs. 1,23,456.78"),
        (1_000_000_000, "Rs. 1,00,00,000.00"),
    ],
)
def test_format_inr(paise, expected):
    assert format_inr(paise) == expected


def test_redact_masks_secret_keys_recursively():
    data = {"password": "x", "nested": {"api_key": "y", "ok": 1}, "authorization": "Bearer t"}
    assert redact(data) == {
        "password": "[REDACTED]",
        "nested": {"api_key": "[REDACTED]", "ok": 1},
        "authorization": "[REDACTED]",
    }


PRODUCTION = {
    "app_env": "production",
    "app_base_url": "https://api.brightway.example",
    "database_url": "postgresql://u:p@db/x",
    "supabase_url": "https://x.supabase.co",
    "supabase_publishable_key": "sb_publishable_x",
    "supabase_service_role_key": "sb_secret_x",
    "razorpay_key_id": "rzp_live_x",
    "razorpay_key_secret": "secret",
    "razorpay_webhook_secret": "whsec",
    "cors_origins": "https://brightway.example",
}


def test_valid_production_settings():
    settings = Settings(_env_file=None, **PRODUCTION)  # type: ignore[call-arg]
    assert settings.resolved_payment_provider == "razorpay"
    assert settings.resolved_storage_backend == "supabase"
    assert settings.docs_enabled is False


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"payment_provider": "mock"}, "mock payment provider"),
        ({"supabase_service_role_key": ""}, "local disk storage"),
        ({"app_base_url": "http://api.example"}, "https"),
        ({"cors_origins": "*"}, "explicit origins"),
        ({"razorpay_webhook_secret": ""}, "RAZORPAY_WEBHOOK_SECRET"),
    ],
)
def test_unsafe_production_settings_are_refused(override, message):
    with pytest.raises(ValidationError, match=message):
        Settings(_env_file=None, **{**PRODUCTION, **override})  # type: ignore[call-arg]


def test_development_defaults_to_mock_and_local_storage():
    settings = Settings(_env_file=None, database_url="postgresql://x/y")  # type: ignore[call-arg]
    assert settings.resolved_payment_provider == "mock"
    assert settings.resolved_storage_backend == "local"
