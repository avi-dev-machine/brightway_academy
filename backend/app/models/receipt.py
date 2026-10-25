from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


class Receipt(BaseModel):
    id: UUID
    receipt_number: str
    payment_id: UUID
    student_id: UUID
    fee_id: UUID
    amount_paise: int
    issued_at: datetime
    created_at: datetime
    pdf_path: str | None = Field(default=None, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_pdf(self) -> bool:
        return self.pdf_path is not None
