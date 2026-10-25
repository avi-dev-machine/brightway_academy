"""HTTP contract tests for external adapters (no network): Supabase Auth and Storage,
WhatsApp Cloud API, Fast2SMS, plus storage path safety and the rate limiter."""

import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from app.exceptions import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    RateLimitedError,
    ServiceNotConfiguredError,
    UnauthorizedError,
)
from app.integrations.notifications import OutgoingMessage, PermanentDeliveryError
from app.integrations.sms.client import Fast2SmsClient
from app.integrations.sms.service import SmsProvider
from app.integrations.storage.client import (
    LocalStorageBackend,
    SupabaseStorageBackend,
    validate_object_path,
)
from app.integrations.supabase_auth import SupabaseAuthClient
from app.integrations.whatsapp.client import WhatsAppClient
from app.integrations.whatsapp.service import WhatsAppProvider, parse_status_updates
from app.utils.rate_limit import RateLimiter

TOKEN_RESPONSE = {
    "access_token": "a.b.c",
    "refresh_token": "refresh-token-value",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {"id": str(uuid4())},
}


def mock(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------- Supabase Auth
def auth_client(handler, service_key: str = "") -> SupabaseAuthClient:
    return SupabaseAuthClient(
        "https://x.supabase.co", "sb_publishable_x", service_key, transport=mock(handler)
    )


def test_password_sign_in_request_shape():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(
            url=str(request.url), apikey=request.headers["apikey"], body=json.loads(request.content)
        )
        return httpx.Response(200, json=TOKEN_RESPONSE)

    assert (
        auth_client(handler).sign_in_with_password("a@b.co", "pw123456")["access_token"] == "a.b.c"
    )
    assert seen["url"] == "https://x.supabase.co/auth/v1/token?grant_type=password"
    assert seen["apikey"] == "sb_publishable_x"
    assert seen["body"] == {"email": "a@b.co", "password": "pw123456"}


@pytest.mark.parametrize(
    ("status", "body", "error", "code"),
    [
        (400, {"error_code": "invalid_credentials"}, UnauthorizedError, "INVALID_CREDENTIALS"),
        (400, {"error_code": "email_not_confirmed"}, UnauthorizedError, "EMAIL_NOT_CONFIRMED"),
        (429, {}, RateLimitedError, "RATE_LIMITED"),
        (500, {}, ExternalServiceError, "EXTERNAL_SERVICE_ERROR"),
    ],
)
def test_sign_in_errors(status, body, error, code):
    client = auth_client(lambda _r: httpx.Response(status, json=body))
    with pytest.raises(error) as info:
        client.sign_in_with_password("a@b.co", "pw123456")
    assert info.value.code == code


def test_invite_requires_service_key_and_maps_existing_user():
    with pytest.raises(ServiceNotConfiguredError):
        auth_client(lambda _r: httpx.Response(200)).invite_user("a@b.co")
    user_id = uuid4()
    ok = auth_client(lambda _r: httpx.Response(200, json={"id": str(user_id)}), "sb_secret_x")
    assert ok.invite_user("a@b.co") == user_id
    exists = auth_client(lambda _r: httpx.Response(422, json={}), "sb_secret_x")
    with pytest.raises(ConflictError):
        exists.invite_user("a@b.co")


def test_login_endpoint(client, container):
    container.auth_client = auth_client(lambda _r: httpx.Response(200, json=TOKEN_RESPONSE))
    response = client.post("/api/v1/auth/login", json={"email": "a@b.co", "password": "pw123456"})
    assert response.status_code == 200
    assert response.json()["data"]["refresh_token"] == "refresh-token-value"
    container.auth_client = auth_client(lambda _r: httpx.Response(400, json={}))
    denied = client.post("/api/v1/auth/login", json={"email": "a@b.co", "password": "wrong-pw"})
    assert denied.status_code == 401 and denied.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_is_rate_limited(client, container):
    container.auth_client = auth_client(lambda _r: httpx.Response(400, json={}))
    container.login_limiter = RateLimiter(2, 60)
    codes = [
        client.post(
            "/api/v1/auth/login", json={"email": "a@b.co", "password": "wrong-pw"}
        ).status_code
        for _ in range(3)
    ]
    assert codes == [401, 401, 429]


def test_rate_limiter_window():
    limiter = RateLimiter(2, 60)
    limiter.hit("k")
    limiter.hit("k")
    with pytest.raises(RateLimitedError) as info:
        limiter.hit("k")
    assert int(info.value.headers["Retry-After"]) >= 1
    limiter.hit("other")  # keys are independent


# ---------------------------------------------------------------------- Supabase Storage
def storage(handler) -> SupabaseStorageBackend:
    return SupabaseStorageBackend("https://x.supabase.co", "sb_secret_x", transport=mock(handler))


def test_storage_upload_and_download():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen[request.method] = (
            str(request.url),
            request.headers.get("x-upsert"),
            request.headers["apikey"],
        )
        return httpx.Response(200, content=b"pdf-bytes" if request.method == "GET" else b"{}")

    backend = storage(handler)
    backend.upload("receipts", "s1/R-1.pdf", b"%PDF", "application/pdf", upsert=True)
    assert backend.download("receipts", "s1/R-1.pdf") == b"pdf-bytes"
    assert seen["POST"] == (
        "https://x.supabase.co/storage/v1/object/receipts/s1/R-1.pdf",
        "true",
        "sb_secret_x",
    )
    assert seen["GET"][0].endswith("/object/authenticated/receipts/s1/R-1.pdf")


def test_storage_error_mapping():
    with pytest.raises(ConflictError):
        storage(lambda _r: httpx.Response(400, json={"error": "Duplicate"})).upload(
            "b1", "p.jpg", b"x", "image/jpeg", False
        )
    with pytest.raises(NotFoundError):
        storage(lambda _r: httpx.Response(400, text="Object not found")).download("b1", "p.jpg")
    with pytest.raises(ExternalServiceError):
        storage(lambda _r: httpx.Response(500)).ping()


@pytest.mark.parametrize("path", ["../secret", "a/../../b", "/abs", "a//b", "a/b\\c", ""])
def test_unsafe_storage_paths_are_rejected(path):
    with pytest.raises(ValueError):
        validate_object_path("receipts", path)


def test_local_storage_round_trip_and_no_overwrite(tmp_path: Path):
    backend = LocalStorageBackend(tmp_path)
    backend.upload("b1", "x/y.txt", b"one", "text/plain", upsert=False)
    with pytest.raises(ConflictError):
        backend.upload("b1", "x/y.txt", b"two", "text/plain", upsert=False)
    backend.upload("b1", "x/y.txt", b"two", "text/plain", upsert=True)
    assert backend.download("b1", "x/y.txt") == b"two"
    with pytest.raises(NotFoundError):
        backend.download("b1", "missing.txt")


# ---------------------------------------------------------------------- WhatsApp
MESSAGE = OutgoingMessage(
    recipient="+919876543210",
    template="fee_reminder",
    params={
        "name": "Asha",
        "fee_title": "Tuition",
        "amount": "Rs. 1.00",
        "due_date": "07 Oct 2026",
    },
    text="...",
)


def whatsapp(handler) -> WhatsAppProvider:
    return WhatsAppProvider(WhatsAppClient("token", "12345", transport=mock(handler)))


def test_whatsapp_sends_template_with_ordered_params():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(
            url=str(request.url),
            auth=request.headers["authorization"],
            body=json.loads(request.content),
        )
        return httpx.Response(200, json={"messages": [{"id": "wamid.ABC"}]})

    result = whatsapp(handler).send(MESSAGE)
    assert result.provider_message_id == "wamid.ABC"
    assert seen["url"] == "https://graph.facebook.com/v21.0/12345/messages"
    assert seen["auth"] == "Bearer token"
    assert seen["body"]["to"] == "919876543210"
    template = seen["body"]["template"]
    assert template["name"] == "fee_reminder"
    assert [p["text"] for p in template["components"][0]["parameters"]] == [
        "Asha",
        "Tuition",
        "Rs. 1.00",
        "07 Oct 2026",
    ]


def test_whatsapp_error_classification():
    permanent = whatsapp(
        lambda _r: httpx.Response(400, json={"error": {"code": 131026, "message": "undeliverable"}})
    )
    with pytest.raises(PermanentDeliveryError):
        permanent.send(MESSAGE)
    transient = whatsapp(lambda _r: httpx.Response(503, json={}))
    with pytest.raises(ExternalServiceError) as info:
        transient.send(MESSAGE)
    assert not isinstance(info.value, PermanentDeliveryError)


def test_parse_status_updates_ignores_malformed_entries():
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {
                                    "id": "wamid.1",
                                    "status": "failed",
                                    "errors": [{"title": "Number not on WhatsApp"}],
                                },
                                {"status": "delivered"},
                            ]
                        }
                    }
                ]
            }
        ]
    }
    updates = parse_status_updates(payload)
    assert [(u.message_id, u.status, u.error) for u in updates] == [
        ("wamid.1", "failed", "Number not on WhatsApp")
    ]


# ---------------------------------------------------------------------- SMS
def test_sms_sends_ten_digit_number():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(auth=request.headers["authorization"], body=json.loads(request.content))
        return httpx.Response(200, json={"return": True, "request_id": "req-1"})

    provider = SmsProvider(Fast2SmsClient("api-key", transport=mock(handler)))
    assert provider.send(MESSAGE).provider_message_id == "req-1"
    assert seen["auth"] == "api-key" and seen["body"]["numbers"] == "9876543210"


def test_sms_failures():
    rejected = SmsProvider(
        Fast2SmsClient("k", transport=mock(lambda _r: httpx.Response(400, json={"return": False})))
    )
    with pytest.raises(PermanentDeliveryError):
        rejected.send(MESSAGE)
    foreign = OutgoingMessage("+14155550100", "fee_reminder", {}, "hi")
    with pytest.raises(PermanentDeliveryError):
        rejected.send(foreign)
