"""Small, pure validation and normalisation helpers."""

import re

_WHITESPACE = re.compile(r"\s+")
_NON_DIGITS = re.compile(r"\D")
_PHONE_SEPARATORS = re.compile(r"[/,;|]")
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def normalize_whitespace(value: str | None) -> str | None:
    """Trim and collapse internal whitespace. Empty strings become None."""
    if value is None:
        return None
    cleaned = _WHITESPACE.sub(" ", value).strip()
    return cleaned or None


def normalize_indian_phone(raw: str | None) -> str | None:
    """Return the first valid Indian mobile number in `raw` as E.164 (+91XXXXXXXXXX), else None.

    Legacy records sometimes hold several numbers ("98xxxxxxxx / 97xxxxxxxx"); the raw
    value is always kept separately, this only derives a number usable for messaging.
    """
    if not raw:
        return None
    for part in _PHONE_SEPARATORS.split(raw):
        digits = _NON_DIGITS.sub("", part)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        if len(digits) == 10 and digits[0] in "6789":
            return "+91" + digits
    return None


def escape_like(value: str) -> str:
    """Escape LIKE/ILIKE wildcards so user input is matched literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def sanitize_csv_cell(value: object) -> str:
    """Neutralise spreadsheet formula injection in exported CSV cells."""
    text = "" if value is None else str(value)
    if text.startswith(_CSV_FORMULA_PREFIXES):
        return "'" + text
    return text
