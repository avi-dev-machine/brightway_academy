"""Razorpay adapter: HTTP contract (mocked transport), signatures, error mapping, live sandbox."""

import base64
import json
import os

import httpx
import pytest

from app.config import Settings
from app.exceptions import ExternalServiceError, NotFoundError, ServiceNotConfiguredError
from app.integrations.razorpay.client import RazorpayClient
from app.integrations.razorpay.service import RazorpayPaymentProvider
from app.integrations.razorpay.webhook import checkout_message, compute_signature, parse_event


def provider_with(handler, webhook_secret="whsec_test") -> RazorpayPaymentProvider:
    client = RazorpayClient("rzp_test_key", "test_secret", transport=httpx.MockTransport(handler))
    return RazorpayPaymentProvider(client, webhook_secret)


def test_create_order_sends_basic_auth_and_amount_in_paise():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        seen["url"] = str(request.url)
        return httpx.Response(
            200, json={"id": "order_ABC123def", "amount": 150000, "currency": "INR"}
        )

    order = provider_with(handler).create_order(
        amount_paise=150_000, currency="INR", receipt="r1", notes={"fee_id": "f"}
    )
    assert order.order_id == "order_ABC123def" and order.amount_paise == 150_000
    assert seen["url"] == "https://api.razorpay.com/v1/orders"
    assert seen["auth"] == "Basic " + base64.b64encode(b"rzp_test_key:test_secret").decode()
    assert seen["body"] == {
        "amount": 150000,
        "currency": "INR",
        "receipt": "r1",
        "notes": {"fee_id": "f"},
        "payment_capture": 1,
    }


@pytest.mark.parametrize(
    ("status_code", "error", "code"),
    [
        (401, ExternalServiceError, "PAYMENT_PROVIDER_AUTH"),
        (400, ExternalServiceError, "PAYMENT_PROVIDER_ERROR"),
        (500, ExternalServiceError, "PAYMENT_PROVIDER_ERROR"),
        (404, NotFoundError, "PROVIDER_PAYMENT_NOT_FOUND"),
    ],
)
def test_error_responses_are_mapped(status_code, error, code):
    provider = provider_with(
        lambda _r: httpx.Response(status_code, json={"error": {"description": "nope"}})
    )
    with pytest.raises(error) as info:
        provider.fetch_payment("pay_ABCDEF123456")
    assert info.value.code == code


def test_unknown_id_400_is_mapped_to_not_found():
    # Observed live: Razorpay returns 400 (not 404) for an id that does not exist.
    provider = provider_with(
        lambda _r: httpx.Response(
            400, json={"error": {"description": "The id provided does not exist"}}
        )
    )
    with pytest.raises(NotFoundError):
        provider.fetch_payment("pay_ABCDEF123456")


def test_network_failure_is_an_external_service_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(ExternalServiceError):
        provider_with(handler).create_order(amount_paise=100, currency="INR", receipt="r", notes={})


def test_payment_id_is_validated_before_any_request():
    calls = []
    provider = provider_with(lambda r: calls.append(r) or httpx.Response(200, json={}))
    with pytest.raises(NotFoundError):
        provider.fetch_payment("../orders")
    assert calls == []


def test_checkout_signature_verification():
    provider = provider_with(lambda _r: httpx.Response(200))
    good = compute_signature("test_secret", checkout_message("order_1", "pay_1"))
    assert provider.verify_checkout_signature(
        order_id="order_1", payment_id="pay_1", signature=good
    )
    assert not provider.verify_checkout_signature(
        order_id="order_1", payment_id="pay_2", signature=good
    )


def test_webhook_signature_requires_a_configured_secret():
    body = b'{"event":"payment.captured"}'
    provider = provider_with(lambda _r: httpx.Response(200))
    assert provider.verify_webhook_signature(body, compute_signature("whsec_test", body))
    assert not provider.verify_webhook_signature(body + b" ", compute_signature("whsec_test", body))
    with pytest.raises(ServiceNotConfiguredError):
        provider_with(lambda _r: httpx.Response(200), webhook_secret="").verify_webhook_signature(
            body, "x"
        )


def test_parse_order_paid_event():
    body = json.dumps(
        {
            "event": "order.paid",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_1",
                        "order_id": "order_1",
                        "amount": 500,
                        "currency": "INR",
                        "status": "captured",
                        "method": "upi",
                    }
                },
                "order": {"entity": {"id": "order_1"}},
            },
        }
    ).encode()
    event = parse_event(body, "evt_1")
    assert event.event_id == "evt_1" and event.order_id == "order_1"
    assert event.payment is not None and event.payment.status == "captured"


def test_malformed_webhook_payload():
    from app.exceptions import PaymentVerificationError

    for body in (
        b"not json",
        b"[]",
        b'{"event": "payment.captured", "payload": {"payment": {"entity": {"id": "x"}}}}',
    ):
        with pytest.raises(PaymentVerificationError):
            parse_event(body, None)


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_TESTS") != "1",
    reason="set RUN_LIVE_TESTS=1 to call Razorpay test mode",
)
def test_live_razorpay_test_mode_order():
    settings = Settings()
    if not settings.razorpay_key_id.startswith("rzp_test_"):
        pytest.skip("live test only runs with Razorpay *test* keys")
    client = RazorpayClient(
        settings.razorpay_key_id, settings.razorpay_key_secret.get_secret_value()
    )
    provider = RazorpayPaymentProvider(client, "")
    try:
        order = provider.create_order(
            amount_paise=100,
            currency="INR",
            receipt="brightway-live-test",
            notes={"purpose": "test"},
        )
        assert order.order_id.startswith("order_") and order.amount_paise == 100
        with pytest.raises(NotFoundError):
            provider.fetch_payment("pay_doesnotexist0001")
    finally:
        provider.close()
