"""Application configuration, loaded from environment variables and backend/.env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_base_url: str = "http://localhost:8000"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    cors_origins: str = ""
    expose_api_docs: bool | None = None
    timezone: str = "Asia/Kolkata"

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_service_role_key: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("")
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10

    payment_provider: Literal["razorpay", "mock"] | None = None
    razorpay_key_id: str = ""
    razorpay_key_secret: SecretStr = SecretStr("")
    razorpay_webhook_secret: SecretStr = SecretStr("")
    razorpay_api_base: str = "https://api.razorpay.com/v1"

    # "meta" = WhatsApp Cloud API directly; "fast2sms" = WhatsApp through Fast2SMS, where
    # WHATSAPP_ACCESS_TOKEN is the Fast2SMS API key and templates are Fast2SMS message ids.
    whatsapp_provider: Literal["meta", "fast2sms"] = "meta"
    whatsapp_access_token: SecretStr = SecretStr("")
    whatsapp_phone_number_id: str = ""
    # Approved template per message type: Meta template name or Fast2SMS message_id.
    whatsapp_template_fee_reminder: str = ""
    whatsapp_template_payment_success: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_webhook_verify_token: SecretStr = SecretStr("")
    whatsapp_app_secret: SecretStr = SecretStr("")
    whatsapp_api_version: str = "v21.0"
    whatsapp_template_language: str = "en"

    sms_provider: Literal["fast2sms"] | None = None
    sms_provider_api_key: SecretStr = SecretStr("")
    sms_sender_id: str = ""
    email_api_key: SecretStr = SecretStr("")

    storage_backend: Literal["supabase", "local"] | None = None
    local_storage_dir: str = ".storage"
    student_photo_bucket: str = "student-photos"
    id_card_bucket: str = "id-cards"
    receipt_bucket: str = "receipts"
    academy_assets_bucket: str = "academy-assets"

    max_photo_bytes: int = 5 * 1024 * 1024
    max_csv_bytes: int = 5 * 1024 * 1024
    max_csv_rows: int = 20_000
    pdf_font_path: str = ""
    pdf_font_bold_path: str = ""

    scheduler_interval_seconds: int = 60
    login_rate_limit_per_minute: int = 10
    webhook_rate_limit_per_minute: int = 300

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def docs_enabled(self) -> bool:
        if self.expose_api_docs is not None:
            return self.expose_api_docs
        return not self.is_production

    @property
    def resolved_payment_provider(self) -> str:
        if self.payment_provider:
            return self.payment_provider
        if self.razorpay_key_id and self.razorpay_key_secret.get_secret_value():
            return "razorpay"
        return "mock"

    @property
    def resolved_storage_backend(self) -> str:
        if self.storage_backend:
            return self.storage_backend
        return "supabase" if self.supabase_service_role_key.get_secret_value() else "local"

    @property
    def whatsapp_templates(self) -> dict[str, str]:
        """Internal template key -> provider template (only the ones configured)."""
        templates = {
            "fee_reminder": self.whatsapp_template_fee_reminder,
            "payment_success": self.whatsapp_template_payment_success,
        }
        return {key: value for key, value in templates.items() if value}

    @property
    def whatsapp_configured(self) -> bool:
        if not (self.whatsapp_access_token.get_secret_value() and self.whatsapp_phone_number_id):
            return False
        # Fast2SMS has no template naming convention to fall back on: every id is required.
        return self.whatsapp_provider == "meta" or len(self.whatsapp_templates) == 2

    @property
    def sms_configured(self) -> bool:
        return bool(self.sms_provider and self.sms_provider_api_key.get_secret_value())

    @model_validator(mode="after")
    def _validate_production(self) -> "Settings":
        if not self.is_production:
            return self
        problems: list[str] = []
        if not self.database_url.get_secret_value():
            problems.append("DATABASE_URL is required")
        if not self.supabase_url or not self.supabase_publishable_key:
            problems.append("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are required")
        if self.resolved_payment_provider == "mock":
            problems.append("the mock payment provider cannot be used in production")
        if self.resolved_payment_provider == "razorpay" and not (
            self.razorpay_webhook_secret.get_secret_value()
        ):
            problems.append("RAZORPAY_WEBHOOK_SECRET is required")
        if self.resolved_storage_backend == "local":
            problems.append("local disk storage cannot be used in production")
        if "*" in self.cors_origin_list:
            problems.append("CORS_ORIGINS must list explicit origins")
        if not self.app_base_url.startswith("https://"):
            problems.append("APP_BASE_URL must use https")
        if problems:
            raise ValueError("Invalid production configuration: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
