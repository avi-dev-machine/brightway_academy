"""Academy settings and the first-run setup checklist."""

from datetime import UTC, datetime
from typing import TypeVar

from pydantic import BaseModel

from app.core.permissions import CurrentUser
from app.db.client import Database, DbConnection
from app.models.settings import (
    AcademySettings,
    FeeSettings,
    NotificationSettings,
    SettingKey,
    SetupState,
)
from app.repositories.fee_repository import FeePlanRepository
from app.repositories.id_card_repository import IdCardTemplateRepository
from app.repositories.import_repository import ImportJobRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import AllSettings, SetupStatus
from app.services.audit_service import record_audit

M = TypeVar("M", bound=BaseModel)


def load_setting(conn: DbConnection, key: SettingKey, model: type[M]) -> M:
    return model.model_validate(SettingsRepository(conn).get(key.value) or {})


def load_academy(conn: DbConnection) -> AcademySettings:
    return load_setting(conn, SettingKey.ACADEMY, AcademySettings)


class SettingsService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def all(self) -> AllSettings:
        with self.db.transaction() as conn:
            return AllSettings(
                academy=load_academy(conn),
                fees=load_setting(conn, SettingKey.FEES, FeeSettings),
                notifications=load_setting(conn, SettingKey.NOTIFICATIONS, NotificationSettings),
                setup=load_setting(conn, SettingKey.SETUP, SetupState),
            )

    def update(self, actor: CurrentUser, key: SettingKey, value: M) -> M:
        with self.db.transaction() as conn:
            repo = SettingsRepository(conn)
            before = repo.get(key.value)
            stored = repo.upsert(key.value, value.model_dump(mode="json"), actor.user_id)
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="settings.updated",
                entity_type="app_setting",
                entity_id=key.value,
                before=before,
                after=stored,
            )
        return type(value).model_validate(stored)

    def setup_status(self, available_channels: list[str]) -> SetupStatus:
        with self.db.transaction() as conn:
            academy = load_academy(conn)
            setup = load_setting(conn, SettingKey.SETUP, SetupState)
            return SetupStatus(
                academy_configured=bool(academy.name and academy.phone and academy.address),
                admin_exists=UserRepository(conn).count_active_admins() > 0,
                students_count=int(ReportRepository(conn).student_counts()["total"]),
                completed_imports=ImportJobRepository(conn).count_completed(),
                default_id_card_template=IdCardTemplateRepository(conn).get_default() is not None,
                fee_plans_count=len(FeePlanRepository(conn).search(active=True, course_id=None)),
                notification_channels_available=available_channels,
                setup_completed=setup.completed,
                completed_at=setup.completed_at,
            )

    def complete_setup(self, actor: CurrentUser, available_channels: list[str]) -> SetupStatus:
        self.update(
            actor, SettingKey.SETUP, SetupState(completed=True, completed_at=datetime.now(UTC))
        )
        return self.setup_status(available_channels)
