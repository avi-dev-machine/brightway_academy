from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.constants import Role
from app.dependencies import (
    AdminUser,
    ContainerDep,
    audit_service,
    auth_service,
    notification_service,
    settings_service,
)
from app.models.audit import AuditLog
from app.models.settings import AcademySettings, FeeSettings, NotificationSettings, SettingKey
from app.models.user import UserProfile
from app.schemas.admin import AllSettings, SetupStatus, SystemStatus
from app.schemas.auth import InviteUserRequest, LinkUserRequest, UpdateUserRequest
from app.schemas.common import ApiResponse, ok
from app.utils.pagination import PageDep, paged

router = APIRouter()


# ---------------------------------------------------------------------- first-run setup
@router.get("/setup", response_model=ApiResponse[SetupStatus])
def setup_status(user: AdminUser, container: ContainerDep) -> ApiResponse[SetupStatus]:
    channels = notification_service(container).available_channels
    return ok(settings_service(container).setup_status(channels))


@router.post("/setup/complete", response_model=ApiResponse[SetupStatus])
def complete_setup(user: AdminUser, container: ContainerDep) -> ApiResponse[SetupStatus]:
    channels = notification_service(container).available_channels
    return ok(settings_service(container).complete_setup(user, channels))


@router.get("/settings", response_model=ApiResponse[AllSettings])
def get_settings(user: AdminUser, container: ContainerDep) -> ApiResponse[AllSettings]:
    return ok(settings_service(container).all())


@router.put("/settings/academy", response_model=ApiResponse[AcademySettings])
def update_academy_settings(
    payload: AcademySettings, user: AdminUser, container: ContainerDep
) -> ApiResponse[AcademySettings]:
    return ok(settings_service(container).update(user, SettingKey.ACADEMY, payload))


@router.put("/settings/fees", response_model=ApiResponse[FeeSettings])
def update_fee_settings(
    payload: FeeSettings, user: AdminUser, container: ContainerDep
) -> ApiResponse[FeeSettings]:
    return ok(settings_service(container).update(user, SettingKey.FEES, payload))


@router.put("/settings/notifications", response_model=ApiResponse[NotificationSettings])
def update_notification_settings(
    payload: NotificationSettings, user: AdminUser, container: ContainerDep
) -> ApiResponse[NotificationSettings]:
    return ok(settings_service(container).update(user, SettingKey.NOTIFICATIONS, payload))


@router.get("/system/status", response_model=ApiResponse[SystemStatus])
def system_status(user: AdminUser, container: ContainerDep) -> ApiResponse[SystemStatus]:
    s = container.settings
    return ok(
        SystemStatus(
            app_env=s.app_env,
            payment_provider=container.payment_provider.name,
            razorpay_webhook_configured=bool(s.razorpay_webhook_secret.get_secret_value()),
            storage_backend=container.storage.backend_name,
            supabase_admin_configured=container.auth_client.admin_configured,
            notification_channels=notification_service(container).available_channels,
            notification_providers={
                channel.value: provider.name
                for channel, provider in container.notification_providers.items()
            },
            whatsapp_provider=s.whatsapp_provider,
            whatsapp_configured=s.whatsapp_configured,
            sms_configured=s.sms_configured,
        )
    )


# ---------------------------------------------------------------------- accounts
@router.get("/users", response_model=ApiResponse[list[UserProfile]])
def list_users(
    user: AdminUser,
    container: ContainerDep,
    params: PageDep,
    role: Role | None = None,
    active: bool | None = None,
) -> ApiResponse[list[UserProfile]]:
    return paged(auth_service(container).list_users(role=role, active=active, params=params))


@router.post(
    "/users/link", response_model=ApiResponse[UserProfile], status_code=status.HTTP_201_CREATED
)
def link_user(
    payload: LinkUserRequest, user: AdminUser, container: ContainerDep
) -> ApiResponse[UserProfile]:
    """Give an existing Supabase Auth user (by id or email) a role in the application."""
    return ok(auth_service(container).link_user(user, payload))


@router.post(
    "/users/invite", response_model=ApiResponse[UserProfile], status_code=status.HTTP_201_CREATED
)
def invite_user(
    payload: InviteUserRequest, user: AdminUser, container: ContainerDep
) -> ApiResponse[UserProfile]:
    """Create a Supabase Auth user, email them an invite and link the role (needs service key)."""
    return ok(auth_service(container).invite_user(user, payload))


@router.patch("/users/{user_id}", response_model=ApiResponse[UserProfile])
def update_user(
    user_id: UUID, payload: UpdateUserRequest, user: AdminUser, container: ContainerDep
) -> ApiResponse[UserProfile]:
    return ok(auth_service(container).update_user(user, user_id, payload))


# ---------------------------------------------------------------------- audit trail
@router.get("/audit-logs", response_model=ApiResponse[list[AuditLog]])
def list_audit_logs(
    user: AdminUser,
    container: ContainerDep,
    params: PageDep,
    entity_type: Annotated[str | None, Query(max_length=50)] = None,
    entity_id: Annotated[str | None, Query(max_length=100)] = None,
    actor_user_id: UUID | None = None,
    action: Annotated[str | None, Query(max_length=100)] = None,
) -> ApiResponse[list[AuditLog]]:
    return paged(
        audit_service(container).search(
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            action=action,
            params=params,
        )
    )
