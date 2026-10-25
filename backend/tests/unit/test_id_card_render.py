import json
import re

import pytest
from pydantic import ValidationError

from app.db.migrate import MIGRATIONS_DIR
from app.models.id_card import IdCardLayout
from app.services.id_card_service import SAMPLE_CONTEXT, render_id_card_pdf, render_placeholders
from app.utils.pdf import PdfFonts
from tests.factories import image_bytes


def default_layout() -> IdCardLayout:
    seed = (MIGRATIONS_DIR / "0003_seed_defaults.sql").read_text(encoding="utf-8")
    layout_json = re.search(r"'(\{\s*\"width_mm\".*?\})'\s*\)", seed, re.S)
    assert layout_json
    return IdCardLayout.model_validate(json.loads(layout_json.group(1)))


def test_render_placeholders():
    assert (
        render_placeholders("ID: {{ student_id }} / {{name}}", {"student_id": "B1", "name": "Asha"})
        == "ID: B1 / Asha"
    )
    assert render_placeholders("{{address}}", {}) == ""


def test_seeded_layout_is_valid_and_renders():
    pdf = render_id_card_pdf(default_layout(), SAMPLE_CONTEXT, None, PdfFonts())
    assert pdf.startswith(b"%PDF")


def test_render_with_photo_and_long_text():
    context = {**SAMPLE_CONTEXT, "name": "A" * 300, "address": "Very long address " * 40}
    pdf = render_id_card_pdf(default_layout(), context, image_bytes("JPEG"), PdfFonts())
    assert pdf.startswith(b"%PDF") and len(pdf) > 1000


def test_non_latin_text_does_not_crash_with_core_fonts():
    pdf = render_id_card_pdf(
        default_layout(), {**SAMPLE_CONTEXT, "name": "অশা রায়"}, None, PdfFonts()
    )
    assert pdf.startswith(b"%PDF")


def test_unknown_placeholder_is_rejected():
    with pytest.raises(ValidationError, match="Unknown placeholders: password"):
        IdCardLayout.model_validate(
            {
                "width_mm": 85.6,
                "height_mm": 54,
                "elements": [
                    {"type": "text", "x": 1, "y": 1, "w": 10, "h": 5, "text": "{{password}}"}
                ],
            }
        )


def test_out_of_bounds_element_is_rejected():
    with pytest.raises(ValidationError, match="extends beyond the card"):
        IdCardLayout.model_validate(
            {
                "width_mm": 85.6,
                "height_mm": 54,
                "elements": [{"type": "rect", "x": 80, "y": 1, "w": 10, "h": 5}],
            }
        )
