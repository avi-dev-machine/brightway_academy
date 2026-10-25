"""WhatsApp through Fast2SMS: request contract, error classification, provider selection."""

import httpx
import pytest

from app.config import Settings
from app.dependencies import build_notification_providers
from app.exceptions import ExternalServiceError
from app.integrations.notifications import OutgoingMessage, PermanentDeliveryError
from app.integrations.whatsapp.fast2sms import Fast2SmsWhatsAppProvider
from app.integrations.whatsapp.service import WhatsAppProvider
from app.models.notification import NotificationChannel

MESSAGE = OutgoingMessage(
    recipient="+919876543210",
    template="payment_success",
    params={
        "name": "Asha",
        "amount": "Rs. 1,500.00",
        "fee_title": "Oct | Tuition",
        "receipt_number": "BCA-2026-000001",
    },
    text="...",
)
TEMPLATES = {"fee_reminder": "101", "payment_success": "102"}


def provider(handler, templates=TEMPLATES) -> Fast2SmsWhatsAppProvider:
    return Fast2SmsWhatsAppProvider(
        "fast2sms-key", "579519398574288", templates, transport=httpx.MockTransport(handler)
    )


def test_sends_template_by_message_id():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(method=request.method, url=request.url, auth=request.headers["authorization"])
        return httpx.Response(
            200,
            json={"status": True, "message": "Message sent successfully", "request_id": "6a3b2c1d"},
        )

    result = provider(handler).send(MESSAGE)
    assert result.provider_message_id == "6a3b2c1d"
    assert seen["method"] == "GET" and seen["auth"] == "fast2sms-key"
    assert seen["url"].host == "www.fast2sms.com" and seen["url"].path == "/dev/whatsapp"
    params = dict(seen["url"].params)
    assert params == {
        "message_id": "102",
        "phone_number_id": "579519398574288",
        "numbers": "9876543210",
        # Template order: name, amount, fee title, receipt; "|" inside a value is replaced.
        "variables_values": "Asha|Rs. 1,500.00|Oct / Tuition|BCA-2026-000001",
    }


@pytest.mark.parametrize("status", [401, 429, 500, 503])
def test_account_and_server_errors_are_retried(status):
    failing = provider(
        lambda _r: httpx.Response(
            status, json={"return": False, "status_code": 414, "message": "IP is blacklisted"}
        )
    )
    with pytest.raises(ExternalServiceError) as info:
        failing.send(MESSAGE)
    assert not isinstance(info.value, PermanentDeliveryError)


def test_rejected_message_is_permanent():
    rejected = provider(
        lambda _r: httpx.Response(400, json={"status": False, "message": "Invalid template"})
    )
    with pytest.raises(PermanentDeliveryError, match="Invalid template"):
        rejected.send(MESSAGE)
    soft_failure = provider(
        lambda _r: httpx.Response(200, json={"status": False, "message": "No balance"})
    )
    with pytest.raises(PermanentDeliveryError):
        soft_failure.send(MESSAGE)


def test_missing_template_and_foreign_numbers_fail_without_a_request():
    calls: list = []
    no_templates = provider(lambda r: calls.append(r) or httpx.Response(200), templates={})
    with pytest.raises(PermanentDeliveryError, match="template id"):
        no_templates.send(MESSAGE)
    foreign = OutgoingMessage("+14155550100", "payment_success", {}, "")
    with pytest.raises(PermanentDeliveryError):
        provider(lambda r: calls.append(r) or httpx.Response(200)).send(foreign)
    assert calls == []


def settings(**values) -> Settings:
    base = {"database_url": "postgresql://x/y", "app_env": "development"}
    return Settings(_env_file=None, **{**base, **values})  # type: ignore[call-arg]


def test_fast2sms_whatsapp_needs_number_id_and_both_templates():
    partial = settings(
        whatsapp_provider="fast2sms",
        whatsapp_access_token="k",
        whatsapp_phone_number_id="1",
        whatsapp_template_fee_reminder="101",
    )
    assert partial.whatsapp_configured is False
    providers = build_notification_providers(partial)
    assert (
        providers[NotificationChannel.WHATSAPP].name == "log-whatsapp"
    )  # dev fallback, nothing sent

    full = settings(
        whatsapp_provider="fast2sms",
        whatsapp_access_token="k",
        whatsapp_phone_number_id="1",
        whatsapp_template_fee_reminder="101",
        whatsapp_template_payment_success="102",
    )
    assert full.whatsapp_configured is True
    assert isinstance(
        build_notification_providers(full)[NotificationChannel.WHATSAPP], Fast2SmsWhatsAppProvider
    )


def test_meta_provider_uses_configured_template_names():
    meta = settings(
        whatsapp_access_token="EAAG...",
        whatsapp_phone_number_id="1",
        whatsapp_template_fee_reminder="brightway_fee_reminder_v2",
    )
    whatsapp = build_notification_providers(meta)[NotificationChannel.WHATSAPP]
    assert isinstance(whatsapp, WhatsAppProvider)
    assert whatsapp._template_names == {"fee_reminder": "brightway_fee_reminder_v2"}


def test_production_has_no_logging_fallback():
    prod = settings(
        app_env="production",
        app_base_url="https://api.example",
        supabase_url="https://x.supabase.co",
        supabase_publishable_key="p",
        supabase_service_role_key="s",
        razorpay_key_id="rzp_live_x",
        razorpay_key_secret="s",
        razorpay_webhook_secret="w",
        cors_origins="https://example.com",
        sms_provider="fast2sms",
        sms_provider_api_key="k",
    )
    providers = build_notification_providers(prod)
    assert set(providers) == {NotificationChannel.SMS}
