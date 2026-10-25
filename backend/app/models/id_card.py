"""ID-card templates: a validated JSON layout whose text contains {{placeholders}}."""

import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
TEXT_PLACEHOLDERS = frozenset(
    {"academy_name", "student_id", "name", "guardian_name", "course", "contact", "address"}
)
PHOTO_PLACEHOLDER = "{{photo}}"

Color = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]
Mm = Annotated[float, Field(ge=0, le=300)]


class RectElement(BaseModel):
    type: Literal["rect"]
    x: Mm
    y: Mm
    w: Mm
    h: Mm
    fill: Color = "#000000"


class TextElement(BaseModel):
    type: Literal["text"]
    x: Mm
    y: Mm
    w: Mm
    h: Mm
    text: str = Field(max_length=300)
    font_size: float = Field(default=8, ge=4, le=36)
    bold: bool = False
    color: Color = "#000000"
    align: Literal["L", "C", "R"] = "L"
    multiline: bool = False

    @model_validator(mode="after")
    def _check_placeholders(self) -> "TextElement":
        unknown = set(PLACEHOLDER_PATTERN.findall(self.text)) - TEXT_PLACEHOLDERS
        if unknown:
            raise ValueError(f"Unknown placeholders: {', '.join(sorted(unknown))}")
        return self


class ImageElement(BaseModel):
    type: Literal["image"]
    x: Mm
    y: Mm
    w: Mm
    h: Mm
    source: Literal["{{photo}}"] = "{{photo}}"


LayoutElement = Annotated[RectElement | TextElement | ImageElement, Field(discriminator="type")]


class IdCardLayout(BaseModel):
    width_mm: float = Field(gt=10, le=300)
    height_mm: float = Field(gt=10, le=300)
    background_color: Color = "#FFFFFF"
    elements: list[LayoutElement] = Field(max_length=60)

    @model_validator(mode="after")
    def _check_bounds(self) -> "IdCardLayout":
        tolerance = 0.01
        for index, element in enumerate(self.elements):
            if (
                element.x + element.w > self.width_mm + tolerance
                or element.y + element.h > self.height_mm + tolerance
            ):
                raise ValueError(f"Element {index} ({element.type}) extends beyond the card.")
        return self


class IdCardTemplate(BaseModel):
    id: UUID
    name: str
    layout: IdCardLayout
    is_default: bool
    active: bool
    created_at: datetime
    updated_at: datetime


class IdCard(BaseModel):
    id: UUID
    student_id: UUID
    template_id: UUID
    generated_by: UUID | None
    generated_at: datetime
