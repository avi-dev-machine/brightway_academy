"""Receipts: one per successful payment (idempotent), rendered to PDF and stored privately."""

import logging
import re
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from app.core.permissions import CurrentUser
from app.db.client import Database, DbConnection
from app.exceptions import ForbiddenError, NotFoundError, ReceiptGenerationError
from app.integrations.storage.service import StorageService
from app.models.receipt import Receipt
from app.models.settings import AcademySettings
from app.repositories.base import Row
from app.repositories.receipt_repository import ReceiptRepository
from app.services.settings_service import load_academy
from app.utils.dates import local_today
from app.utils.pagination import Page, PageParams
from app.utils.pdf import PdfFonts, format_inr, new_pdf

logger = logging.getLogger(__name__)

_PAGE_W, _PAGE_H, _MARGIN = 148.0, 210.0, 12.0


def receipt_not_found() -> NotFoundError:
    return NotFoundError("Receipt was not found.", code="RECEIPT_NOT_FOUND")


def _payment_mode(detail: dict[str, Any]) -> str:
    method = (detail.get("method") or "").replace("_", " ").title()
    if detail["provider"] == "OFFLINE":
        return method or "Offline"
    return f"Online ({method})" if method else "Online"


def render_receipt_pdf(
    detail: dict[str, Any], academy: AcademySettings, fonts: PdfFonts, timezone: str
) -> bytes:
    doc = new_pdf(fonts, width_mm=_PAGE_W, height_mm=_PAGE_H)
    pdf = doc.pdf
    pdf.add_page()
    width = _PAGE_W - 2 * _MARGIN
    tz = ZoneInfo(timezone)

    def line(
        text: str, size: float, *, bold: bool = False, align: str = "L", height: float = 6
    ) -> None:
        pdf.set_x(_MARGIN)
        pdf.set_font(doc.family, "B" if bold else "", size)
        pdf.cell(width, height, text=doc.text(text), align=align)
        pdf.ln(height)

    def field(label: str, value: str) -> None:
        pdf.set_x(_MARGIN)
        pdf.set_font(doc.family, "B", 9)
        pdf.cell(38, 6, text=doc.text(label))
        pdf.set_font(doc.family, "", 9)
        pdf.cell(width - 38, 6, text=doc.text(value))
        pdf.ln(6)

    pdf.set_y(_MARGIN)
    line(academy.name, 15, bold=True, align="C", height=8)
    if academy.address:
        line(academy.address, 9, align="C", height=5)
    contact = " | ".join(part for part in (academy.phone, academy.email) if part)
    if contact:
        line(contact, 9, align="C", height=5)
    pdf.ln(2)
    pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
    pdf.ln(4)
    line("FEE RECEIPT", 13, bold=True, align="C", height=8)
    pdf.ln(2)

    issued = detail["issued_at"].astimezone(tz)
    field("Receipt No.", detail["receipt_number"])
    field("Date", f"{issued:%d %b %Y}")
    pdf.ln(2)
    field("Student", detail["student_name"])
    field("ID No.", detail["id_no"])
    if detail.get("guardian_name"):
        field("Guardian", detail["guardian_name"])
    if detail.get("course_name"):
        field("Course", detail["course_name"])
    pdf.ln(4)

    pdf.set_x(_MARGIN)
    pdf.set_font(doc.family, "B", 9)
    pdf.set_fill_color(235, 235, 235)
    pdf.cell(width - 40, 7, text="Description", border=1, fill=True)
    pdf.cell(40, 7, text="Amount", border=1, align="R", fill=True)
    pdf.ln(7)
    pdf.set_x(_MARGIN)
    pdf.set_font(doc.family, "", 9)
    pdf.cell(width - 40, 7, text=doc.text(detail["fee_title"]), border=1)
    pdf.cell(40, 7, text=format_inr(detail["amount_paise"]), border=1, align="R")
    pdf.ln(7)
    pdf.set_x(_MARGIN)
    pdf.set_font(doc.family, "B", 9)
    pdf.cell(width - 40, 7, text="Total received", border=1)
    pdf.cell(40, 7, text=format_inr(detail["amount_paise"]), border=1, align="R")
    pdf.ln(11)

    field("Payment mode", _payment_mode(detail))
    reference = detail.get("provider_payment_id") or detail.get("reference")
    if reference:
        field("Reference", reference)
    if detail.get("paid_at"):
        field("Paid on", f"{detail['paid_at'].astimezone(tz):%d %b %Y %H:%M}")

    pdf.set_y(_PAGE_H - 20)
    line("This is a computer-generated receipt and does not require a signature.", 8, align="C")
    return doc.output()


class ReceiptService:
    def __init__(
        self, db: Database, storage: StorageService, fonts: PdfFonts, timezone: str
    ) -> None:
        self.db = db
        self.storage = storage
        self.fonts = fonts
        self.timezone = timezone

    def create_record(self, conn: DbConnection, payment: Row) -> Row:
        """Create the receipt for a successful payment inside the payment's transaction.
        Idempotent: an existing receipt for the payment is returned unchanged."""
        repo = ReceiptRepository(conn)
        existing = repo.get_by_payment(payment["id"])
        if existing is not None:
            return existing
        prefix = load_academy(conn).receipt_prefix
        number = f"{prefix}-{local_today(self.timezone).year}-{repo.next_number():06d}"
        return repo.create_if_absent(
            receipt_number=number,
            payment_id=payment["id"],
            student_id=payment["student_id"],
            fee_id=payment["fee_id"],
            amount_paise=payment["amount_paise"],
        )

    def ensure_pdf(self, receipt_id: UUID) -> Row:
        with self.db.transaction() as conn:
            detail = ReceiptRepository(conn).detail(receipt_id)
            academy = load_academy(conn)
        if detail is None:
            raise receipt_not_found()
        if detail["pdf_path"]:
            return detail
        try:
            pdf = render_receipt_pdf(detail, academy, self.fonts, self.timezone)
        except Exception as exc:
            logger.error(
                "receipt rendering failed", exc_info=exc, extra={"receipt_id": str(receipt_id)}
            )
            raise ReceiptGenerationError() from exc
        safe_number = re.sub(r"[^A-Za-z0-9-]", "-", detail["receipt_number"])
        path = f"{detail['student_id']}/{safe_number}.pdf"
        # Deterministic path + upsert: concurrent generations write identical content.
        self.storage.upload(self.storage.receipt_bucket, path, pdf, "application/pdf", upsert=True)
        with self.db.transaction() as conn:
            ReceiptRepository(conn).set_pdf_path(receipt_id, path)
        return {**detail, "pdf_path": path}

    def get(self, user: CurrentUser, receipt_id: UUID) -> Receipt:
        with self.db.transaction() as conn:
            row = ReceiptRepository(conn).get_by_id(receipt_id)
        if row is None:
            raise receipt_not_found()
        self._ensure_access(user, row)
        return Receipt.model_validate(row)

    def search(
        self, user: CurrentUser, *, student_id: UUID | None, params: PageParams
    ) -> Page[Receipt]:
        if user.is_teacher:
            raise ForbiddenError()
        if user.is_student:
            if student_id is not None and student_id != user.student_id:
                raise ForbiddenError("You can only view your own receipts.")
            student_id = user.student_id
        with self.db.transaction() as conn:
            rows, total = ReceiptRepository(conn).search(
                student_id=student_id, limit=params.limit, offset=params.offset
            )
        return Page([Receipt.model_validate(r) for r in rows], total, params)

    def download(self, user: CurrentUser, receipt_id: UUID) -> tuple[str, bytes]:
        receipt = self.get(user, receipt_id)
        detail = self.ensure_pdf(receipt.id)
        data = self.storage.download(self.storage.receipt_bucket, detail["pdf_path"])
        return f"{receipt.receipt_number}.pdf", data

    @staticmethod
    def _ensure_access(user: CurrentUser, receipt: Row) -> None:
        if user.is_admin or (user.is_student and receipt["student_id"] == user.student_id):
            return
        raise ForbiddenError("You do not have access to this receipt.")
