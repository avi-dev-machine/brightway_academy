from datetime import datetime

from pydantic import BaseModel

from app.models.settings import AcademySettings, FeeSettings, NotificationSettings, SetupState


class AllSettings(BaseModel):
    academy: AcademySettings
    fees: FeeSettings
    notifications: NotificationSettings
    setup: SetupState


class SetupStatus(BaseModel):
    academy_configured: bool
    admin_exists: bool
    students_count: int
    completed_imports: int
    default_id_card_template: bool
    fee_plans_count: int
    notification_channels_available: list[str]
    setup_completed: bool
    completed_at: datetime | None


class SystemStatus(BaseModel):
    """Which integrations are configured. Never includes secret values."""

    app_env: str
    payment_provider: str
    razorpay_webhook_configured: bool
    storage_backend: str
    supabase_admin_configured: bool
    notification_channels: list[str]
    # Channel -> provider; "log-*" providers only log and never send (development fallback).
    notification_providers: dict[str, str]
    whatsapp_provider: str
    whatsapp_configured: bool
    sms_configured: bool
