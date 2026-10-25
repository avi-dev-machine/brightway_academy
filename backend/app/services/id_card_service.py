"""Template-driven ID-card generation (PDF), stored in the private id-cards bucket."""

import logging
from datetime import UTC, datetime
from io import BytesIO
from typing import Any, cast
from uuid import UUID, uuid4

from fpdf.enums import MethodReturnValue
from PIL import Image

from app.core.permissions import CurrentUser, ensure_student_access
from app.db.client import Database
from app.db.transactions import translate_constraint_errors
from app.exceptions import ConflictError, NotFoundError, StudentNotFoundError
from app.integrations.storage.service import StorageService
from app.models.id_card import PLACEHOLDER_PATTERN, IdCard, IdCardLayout, IdCardTemplate
from app.models.settings import AcademySettings
from app.repositories.id_card_repository import IdCardRepository, IdCardTemplateRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.id_card import TemplateCreate, TemplateUpdate
from app.services.audit_service import record_audit
from app.services.settings_service import load_academy
from app.utils.pdf import PdfDocument, PdfFonts, hex_to_rgb, new_pdf

logger = logging.getLogger(__name__)

_PT_TO_MM = 0.3528
_MIN_FONT_SIZE = 5.0
SAMPLE_CONTEXT = {
    "academy_name": "Brightway Computer Academy",
    "student_id": "BCA00001",
    "name": "Sample Student",
    "guardian_name": "Sample Guardian",
    "course": "Diploma in Computer Applications",
    "contact": "+91 98765 43210",
    "address": "12 Example Road, Sample Town, West Bengal 700001",
}

_TEMPLATE_CONSTRAINTS = {
    "id_card_templates_name_key": lambda: ConflictError(
        "A template with this name already exists.", code="DUPLICATE_TEMPLATE_NAME"
    ),
}


def render_placeholders(text: str, context: dict[str, str]) -> str:
    return PLACEHOLDER_PATTERN.sub(lambda match: context.get(match.group(1), ""), text)


def build_context(student: dict[str, Any], academy: AcademySettings) -> dict[str, str]:
    return {
        "academy_name": academy.name,
        "student_id": student["id_no"],
        "name": student["name"],
        "guardian_name": student.get("guardian_name") or "",
        "course": student.get("course_name") or student.get("legacy_course") or "",
        "contact": student.get("contact") or "",
        "address": student.get("address") or "",
    }


def _fit_single_line(doc: PdfDocument, text: str, width: float, size: float, style: str) -> str:
    """Shrink the font until the text fits; truncate with an ellipsis as a last resort."""
    pdf = doc.pdf
    while size > _MIN_FONT_SIZE and pdf.get_string_width(text) > width:
        size -= 0.5
        pdf.set_font(doc.family, style, size)
    if pdf.get_string_width(text) <= width:
        return text
    while text and pdf.get_string_width(text + "...") > width:
        text = text[:-1]
    return text + "..."


def render_id_card_pdf(
    layout: IdCardLayout, context: dict[str, str], photo: bytes | None, fonts: PdfFonts
) -> bytes:
    doc = new_pdf(fonts, width_mm=layout.width_mm, height_mm=layout.height_mm)
    pdf = doc.pdf
    pdf.add_page()
    pdf.set_fill_color(*hex_to_rgb(layout.background_color))
    pdf.rect(0, 0, layout.width_mm, layout.height_mm, style="F")

    for element in layout.elements:
        if element.type == "rect":
            pdf.set_fill_color(*hex_to_rgb(element.fill))
            pdf.rect(element.x, element.y, element.w, element.h, style="F")
        elif element.type == "image":
            if photo:
                with Image.open(BytesIO(photo)) as image:
                    width_px, height_px = image.size
                scale = min(element.w / width_px, element.h / height_px)
                draw_w, draw_h = width_px * scale, height_px * scale
                pdf.image(
                    BytesIO(photo),
                    x=element.x + (element.w - draw_w) / 2,
                    y=element.y + (element.h - draw_h) / 2,
                    w=draw_w,
                    h=draw_h,
                )
            else:
                pdf.set_draw_color(150, 150, 150)
                pdf.rect(element.x, element.y, element.w, element.h, style="D")
                pdf.set_font(doc.family, "", 6)
                pdf.set_text_color(150, 150, 150)
                pdf.set_xy(element.x, element.y + element.h / 2 - 2)
                pdf.cell(element.w, 4, text="PHOTO", align="C")
        else:
            style = "B" if element.bold else ""
            pdf.set_font(doc.family, style, element.font_size)
            pdf.set_text_color(*hex_to_rgb(element.color))
            content = doc.text(render_placeholders(element.text, context))
            line_height = element.font_size * _PT_TO_MM * 1.2
            pdf.set_xy(element.x, element.y)
            if element.multiline:
                lines = cast(
                    list[str],
                    pdf.multi_cell(
                        element.w,
                        line_height,
                        text=content,
                        align=element.align,
                        dry_run=True,
                        output=MethodReturnValue.LINES,
                    ),
                )
                max_lines = max(int(element.h // line_height), 1)
                if len(lines) > max_lines:
                    lines = [*lines[: max_lines - 1], lines[max_lines - 1].rstrip() + "..."]
                pdf.set_xy(element.x, element.y)
                pdf.multi_cell(element.w, line_height, text="\n".join(lines), align=element.align)
            else:
                content = _fit_single_line(doc, content, element.w, element.font_size, style)
                pdf.cell(element.w, element.h, text=content, align=element.align)
    return doc.output()


class IdCardService:
    def __init__(self, db: Database, storage: StorageService, fonts: PdfFonts) -> None:
        self.db = db
        self.storage = storage
        self.fonts = fonts

    # ------------------------------------------------------------------ templates
    def list_templates(self) -> list[IdCardTemplate]:
        with self.db.transaction() as conn:
            rows = IdCardTemplateRepository(conn).search()
        return [IdCardTemplate.model_validate(r) for r in rows]

    def create_template(self, actor: CurrentUser, payload: TemplateCreate) -> IdCardTemplate:
        with self.db.transaction() as conn:
            repo = IdCardTemplateRepository(conn)
            if payload.is_default:
                repo.clear_default()
            with translate_constraint_errors(_TEMPLATE_CONSTRAINTS):
                row = repo.insert(
                    {
                        "name": payload.name,
                        "layout": payload.layout.model_dump(mode="json"),
                        "is_default": payload.is_default,
                    }
                )
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="id_card_template.created",
                entity_type="id_card_template",
                entity_id=row["id"],
                after=row,
            )
        return IdCardTemplate.model_validate(row)

    def update_template(
        self, actor: CurrentUser, template_id: UUID, payload: TemplateUpdate
    ) -> IdCardTemplate:
        changes: dict[str, Any] = payload.model_dump(exclude_unset=True, exclude={"layout"})
        if payload.layout is not None:
            changes["layout"] = payload.layout.model_dump(mode="json")
        with self.db.transaction() as conn:
            repo = IdCardTemplateRepository(conn)
            current = repo.get_by_id(template_id, for_update=True)
            if current is None:
                raise NotFoundError("Template was not found.", code="TEMPLATE_NOT_FOUND")
            if changes.get("is_default"):
                repo.clear_default()
            with translate_constraint_errors(_TEMPLATE_CONSTRAINTS):
                row = repo.update_fields(template_id, changes)
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="id_card_template.updated",
                entity_type="id_card_template",
                entity_id=template_id,
                before=current,
                after=row,
            )
        return IdCardTemplate.model_validate(row)

    def preview_template(self, template_id: UUID) -> bytes:
        with self.db.transaction() as conn:
            row = IdCardTemplateRepository(conn).get_by_id(template_id)
            academy = load_academy(conn)
        if row is None:
            raise NotFoundError("Template was not found.", code="TEMPLATE_NOT_FOUND")
        context = {**SAMPLE_CONTEXT, "academy_name": academy.name}
        return render_id_card_pdf(
            IdCardLayout.model_validate(row["layout"]), context, None, self.fonts
        )

    # ------------------------------------------------------------------ cards
    def generate(
        self, actor: CurrentUser, student_id: UUID, template_id: UUID | None = None
    ) -> IdCard:
        with self.db.transaction() as conn:
            student = StudentRepository(conn).get(student_id)
            if student is None:
                raise StudentNotFoundError()
            templates = IdCardTemplateRepository(conn)
            template = templates.get_by_id(template_id) if template_id else templates.get_default()
            if template is None or not template["active"]:
                raise NotFoundError(
                    "No active ID-card template is configured.", code="TEMPLATE_NOT_FOUND"
                )
            academy = load_academy(conn)

        photo = None
        if student["photo_path"]:
            photo = self.storage.download(self.storage.photo_bucket, student["photo_path"])
        pdf = render_id_card_pdf(
            IdCardLayout.model_validate(template["layout"]),
            build_context(student, academy),
            photo,
            self.fonts,
        )
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        path = f"{student_id}/{stamp}-{uuid4().hex[:8]}.pdf"
        self.storage.upload(self.storage.id_card_bucket, path, pdf, "application/pdf")

        with self.db.transaction() as conn:
            row = IdCardRepository(conn).insert(
                {
                    "student_id": student_id,
                    "template_id": template["id"],
                    "file_path": path,
                    "generated_by": actor.user_id,
                }
            )
            StudentRepository(conn).update_fields(student_id, {"id_card_path": path})
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="id_card.generated",
                entity_type="student",
                entity_id=student_id,
                after={"id_card_id": str(row["id"]), "template_id": str(template["id"])},
            )
        return IdCard.model_validate(row)

    def download_latest(self, user: CurrentUser, student_id: UUID) -> bytes:
        with self.db.transaction() as conn:
            ensure_student_access(conn, user, student_id)
            student = StudentRepository(conn).get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError()
        if not student["id_card_path"]:
            raise NotFoundError("The ID card has not been generated yet.", code="ID_CARD_NOT_FOUND")
        return self.storage.download(self.storage.id_card_bucket, student["id_card_path"])

    def history(self, student_id: UUID) -> list[IdCard]:
        with self.db.transaction() as conn:
            rows = IdCardRepository(conn).list_for_student(student_id)
        return [IdCard.model_validate(r) for r in rows]
