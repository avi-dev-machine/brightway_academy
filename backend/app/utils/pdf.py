"""Shared PDF helpers (fpdf2) for receipts and ID cards."""

from dataclasses import dataclass
from pathlib import Path

from fpdf import FPDF

CORE_FONT = "helvetica"
UNICODE_FONT = "body"


@dataclass(frozen=True)
class PdfFonts:
    """Optional TTF fonts. Without them PDFs use Helvetica, which only covers Latin-1."""

    regular_path: str = ""
    bold_path: str = ""


@dataclass
class PdfDocument:
    pdf: FPDF
    family: str

    @property
    def unicode(self) -> bool:
        return self.family == UNICODE_FONT

    def text(self, value: str) -> str:
        """Make text safe for the active font (core fonts cannot encode non-Latin-1)."""
        if self.unicode:
            return value
        return value.encode("latin-1", "replace").decode("latin-1")

    def output(self) -> bytes:
        return bytes(self.pdf.output())


def new_pdf(fonts: PdfFonts, *, width_mm: float, height_mm: float) -> PdfDocument:
    pdf = FPDF(orientation="P", unit="mm", format=(width_mm, height_mm))
    pdf.set_auto_page_break(False)
    pdf.set_margins(0, 0, 0)
    family = CORE_FONT
    if fonts.regular_path and Path(fonts.regular_path).is_file():
        bold = fonts.bold_path if fonts.bold_path and Path(fonts.bold_path).is_file() else None
        pdf.add_font(UNICODE_FONT, "", fonts.regular_path)
        pdf.add_font(UNICODE_FONT, "B", bold or fonts.regular_path)
        family = UNICODE_FONT
    return PdfDocument(pdf, family)


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def format_inr(paise: int) -> str:
    """Format paise as Indian rupees with lakh/crore grouping, e.g. Rs. 1,23,456.50."""
    sign = "-" if paise < 0 else ""
    rupees, remainder = divmod(abs(paise), 100)
    digits = str(rupees)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    return f"{sign}Rs. {digits}.{remainder:02d}"
