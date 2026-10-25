"""Dependency container, service factories and FastAPI auth/role dependencies."""

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.core.constants import Role
from app.core.permissions import CurrentUser
from app.core.security import TokenVerifier
from app.db.client import Database
from app.exceptions import ForbiddenError, UnauthorizedError
from app.integrations.mock_payment import MockPaymentProvider
from app.integrations.notifications import LoggingNotificationProvider, NotificationProvider
from app.integrations.payments import PaymentProvider
from app.integrations.razorpay.client import RazorpayClient
from app.integrations.razorpay.service import RazorpayPaymentProvider
from app.integrations.sms.client import Fast2SmsClient
from app.integrations.sms.service import SmsProvider
from app.integrations.storage.service import StorageService
from app.integrations.supabase_auth import SupabaseAuthClient
from app.integrations.whatsapp.client import WhatsAppClient
from app.integrations.whatsapp.fast2sms import Fast2SmsWhatsAppProvider
from app.integrations.whatsapp.service import WhatsAppProvider
from app.logging import user_id_var
from app.models.notification import NotificationChannel
from app.services.attendance_service import AttendanceService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.batch_service import BatchService
from app.services.course_service import CourseService
from app.services.csv_import_service import CsvImportService
from app.services.fee_service import FeeService
from app.services.id_card_service import IdCardService
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService
from app.services.receipt_service import ReceiptService
from app.services.report_service import ReportService
from app.services.settings_service import SettingsService
from app.services.student_service import StudentService
from app.services.teacher_service import TeacherService
from app.utils.pdf import PdfFonts
from app.utils.rate_limit import RateLimiter


@dataclass
class Container:
    settings: Settings
    db: Database
    token_verifier: TokenVerifier
    auth_client: SupabaseAuthClient
    storage: StorageService
    payment_provider: PaymentProvider
    notification_providers: dict[NotificationChannel, NotificationProvider]
    login_limiter: RateLimiter
    webhook_limiter: RateLimiter

    @property
    def pdf_fonts(self) -> PdfFonts:
        return PdfFonts(self.settings.pdf_font_path, self.settings.pdf_font_bold_path)

    def open(self) -> None:
        self.db.open()

    def close(self) -> None:
        self.db.close()
        resources: list[Any] = [self.auth_client, self.storage, self.payment_provider]
        resources.extend(self.notification_providers.values())
        for resource in resources:
            close = getattr(resource, "close", None)
            if callable(close):
                close()


def build_payment_provider(settings: Settings) -> PaymentProvider:
    if settings.resolved_payment_provider == "razorpay":
        client = RazorpayClient(
            settings.razorpay_key_id,
            settings.razorpay_key_secret.get_secret_value(),
            base_url=settings.razorpay_api_base,
        )
        return RazorpayPaymentProvider(client, settings.razorpay_webhook_secret.get_secret_value())
    return MockPaymentProvider()


def build_notification_providers(
    settings: Settings,
) -> dict[NotificationChannel, NotificationProvider]:
    """Real providers for configured channels. Outside production, unconfigured WhatsApp/SMS
    fall back to a provider that only logs, so the pipeline can be exercised locally."""
    providers: dict[NotificationChannel, NotificationProvider] = {}
    if settings.whatsapp_configured:
        token = settings.whatsapp_access_token.get_secret_value()
        if settings.whatsapp_provider == "fast2sms":
            providers[NotificationChannel.WHATSAPP] = Fast2SmsWhatsAppProvider(
                token, settings.whatsapp_phone_number_id, settings.whatsapp_templates
            )
        else:
            providers[NotificationChannel.WHATSAPP] = WhatsAppProvider(
                WhatsAppClient(
                    token,
                    settings.whatsapp_phone_number_id,
                    api_version=settings.whatsapp_api_version,
                ),
                language=settings.whatsapp_template_language,
                template_names=settings.whatsapp_templates,
            )
    if settings.sms_configured:
        providers[NotificationChannel.SMS] = SmsProvider(
            Fast2SmsClient(settings.sms_provider_api_key.get_secret_value())
        )
    if not settings.is_production:
        for channel in (NotificationChannel.WHATSAPP, NotificationChannel.SMS):
            providers.setdefault(channel, LoggingNotificationProvider(channel))
    return providers


def build_container(settings: Settings) -> Container:
    return Container(
        settings=settings,
        db=Database(
            settings.database_url.get_secret_value(),
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
        ),
        token_verifier=TokenVerifier.for_supabase(settings.supabase_url),
        auth_client=SupabaseAuthClient(
            settings.supabase_url,
            settings.supabase_publishable_key,
            settings.supabase_service_role_key.get_secret_value(),
        ),
        storage=StorageService.from_settings(settings),
        payment_provider=build_payment_provider(settings),
        notification_providers=build_notification_providers(settings),
        login_limiter=RateLimiter(settings.login_rate_limit_per_minute, 60),
        webhook_limiter=RateLimiter(settings.webhook_rate_limit_per_minute, 60),
    )


# ---------------------------------------------------------------------- service factories
# Plain functions so that API routes, workers and scripts build services the same way.


def auth_service(c: Container) -> AuthService:
    return AuthService(c.db, c.auth_client)


def audit_service(c: Container) -> AuditService:
    return AuditService(c.db)


def settings_service(c: Container) -> SettingsService:
    return SettingsService(c.db)


def course_service(c: Container) -> CourseService:
    return CourseService(c.db)


def teacher_service(c: Container) -> TeacherService:
    return TeacherService(c.db)


def batch_service(c: Container) -> BatchService:
    return BatchService(c.db)


def id_card_service(c: Container) -> IdCardService:
    return IdCardService(c.db, c.storage, c.pdf_fonts)


def student_service(c: Container) -> StudentService:
    return StudentService(
        c.db,
        c.storage,
        id_card_service(c),
        max_photo_bytes=c.settings.max_photo_bytes,
        timezone=c.settings.timezone,
    )


def csv_import_service(c: Container) -> CsvImportService:
    return CsvImportService(
        c.db, max_bytes=c.settings.max_csv_bytes, max_rows=c.settings.max_csv_rows
    )


def fee_service(c: Container) -> FeeService:
    return FeeService(c.db, c.settings.timezone)


def notification_service(c: Container) -> NotificationService:
    return NotificationService(c.db, c.notification_providers)


def receipt_service(c: Container) -> ReceiptService:
    return ReceiptService(c.db, c.storage, c.pdf_fonts, c.settings.timezone)


def payment_service(c: Container) -> PaymentService:
    return PaymentService(
        c.db, c.payment_provider, receipt_service(c), notification_service(c), c.settings.timezone
    )


def attendance_service(c: Container) -> AttendanceService:
    return AttendanceService(c.db, c.settings.timezone)


def report_service(c: Container) -> ReportService:
    return ReportService(c.db, c.settings.timezone)


# ---------------------------------------------------------------------- FastAPI dependencies


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]

_bearer = HTTPBearer(auto_error=False, description="Supabase Auth access token")


def _authenticate(container: Container, token: str) -> CurrentUser:
    claims = container.token_verifier.verify(token)
    return auth_service(container).load_current_user(claims)


async def get_current_user(
    request: Request,
    container: ContainerDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if credentials is None:
        raise UnauthorizedError()
    # Token verification may fetch JWKS and loads the profile from the database: keep it
    # off the event loop. The context variable is set here so request logs carry the user.
    user = await run_in_threadpool(_authenticate, container, credentials.credentials)
    request.state.user_id = str(user.user_id)
    user_id_var.set(str(user.user_id))
    return user


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*roles: Role) -> Any:
    async def checker(user: CurrentUserDep) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return Depends(checker)


AdminUser = Annotated[CurrentUser, require_roles(Role.ADMIN)]
StaffUser = Annotated[CurrentUser, require_roles(Role.ADMIN, Role.TEACHER)]
