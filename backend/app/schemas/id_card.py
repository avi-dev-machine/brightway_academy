from uuid import UUID

from pydantic import BaseModel, Field

from app.models.id_card import IdCardLayout


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    layout: IdCardLayout
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    layout: IdCardLayout | None = None
    is_default: bool | None = None
    active: bool | None = None


class GenerateIdCardRequest(BaseModel):
    template_id: UUID | None = Field(default=None, description="Defaults to the default template.")
