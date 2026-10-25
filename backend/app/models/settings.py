"""Academy-level settings stored in the app_settings table (one JSON document per key)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.models.notification import NotificationChannel


class SettingKey(StrEnum):
    ACADEMY = "academy"
    FEES = "fees"
    NOTIFICATIONS = "notifications"
    SETUP = "setup"


class AcademySettings(BaseModel):
    name: str = Field(default="Brightway Computer Academy", min_length=1, max_length=120)
    address: str = Field(default="", max_length=300)
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=254)
    student_id_prefix: str = Field(default="BCA", pattern=r"^[A-Z0-9/-]{0,10}$")
    receipt_prefix: str = Field(default="BCA", pattern=r"^[A-Z0-9-]{1,10}$")


class FeeSettings(BaseModel):
    # Days relative to the due date on which reminders are sent (-3 = three days before).
    reminder_offsets_days: list[int] = Field(default_factory=lambda: [-3, 0, 3, 7], max_length=10)

    @field_validator("reminder_offsets_days")
    @classmethod
    def _check_offsets(cls, value: list[int]) -> list[int]:
        if any(offset < -30 or offset > 90 for offset in value):
            raise ValueError("Reminder offsets must be between -30 and 90 days.")
        return sorted(set(value))


class NotificationSettings(BaseModel):
    channels: list[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.WHATSAPP, NotificationChannel.SMS]
    )
    fee_reminders_enabled: bool = True
    payment_confirmations_enabled: bool = True


class SetupState(BaseModel):
    completed: bool = False
    completed_at: datetime | None = None


SETTING_MODELS: dict[SettingKey, type[BaseModel]] = {
    SettingKey.ACADEMY: AcademySettings,
    SettingKey.FEES: FeeSettings,
    SettingKey.NOTIFICATIONS: NotificationSettings,
    SettingKey.SETUP: SetupState,
}
