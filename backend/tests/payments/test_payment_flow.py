"""Online payment lifecycle through the API with the mock provider (Razorpay-compatible):
orders, checkout verification, webhooks, idempotency, wrong amounts and refunds."""

import json
import re
from typing import Any
from uuid import uuid4

import pytest

from tests.factories import auth_header, make_fee, make_student, make_user


@pytest.fixture
def fee(db, student) -> dict[str, Any]:
    return make_fee(db, student["id"], amount_paise=150_000, title="October tuition")


def create_order(client, headers, fee_id, **body):
    return client.post(
        "/api/v1/payments/orders", json={"fee_id": str(fee_id), **body}, headers=headers
    )


def verify(client, headers, provider, order_id, *, status="captured", amount=None, signature=None):
    payment = provider.simulate_payment(order_id, status=status, amount_paise=amount)
    response = client.post(
        "/api/v1/payments/verify",
        json={
            "provider_order_id": order_id,
            "provider_payment_id": payment.payment_id,
            "signature": signature or provider.checkout_signature(order_id, payment.payment_id),
        },
        headers=headers,
    )
    return response, payment


def webhook(client, provider, event, *, payment=None, refund=None, event_id=None, signature=None):
    payload: dict[str, Any] = {"entity": "event", "event": event, "payload": {}}
    if payment is not None:
        payload["payload"]["payment"] = {
            "entity": {
                "id": payment.payment_id,
                "order_id": payment.order_id,
                "amount": payment.amount_paise,
                "currency": payment.currency,
                "status": payment.status,
                "method": payment.method,
            }
        }
    if refund is not None:
        payload["payload"]["refund"] = {"entity": refund}
    body = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature or provider.webhook_signature(body),
        "X-Razorpay-Event-Id": event_id or f"evt_{uuid4().hex[:14]}",
    }
    return client.post("/api/v1/payments/webhooks/razorpay", content=body, headers=headers)


def one(db, query, *params):
    with db.transaction() as conn:
        return conn.execute(query, params).fetchone()


def count(db, table):
    return one(db, f"select count(*) as n from {table}")["n"]


# ---------------------------------------------------------------------- orders
def test_student_creates_order_for_own_fee(client, student_headers, fee, payment_provider):
    response = create_order(client, student_headers, fee["id"])
    assert response.status_code == 201, response.text
    order = response.json()["data"]
    assert order["amount_paise"] == 150_000
    assert order["currency"] == "INR"
    assert order["key_id"] == "rzp_mock_key"
    assert order["provider_order_id"] in payment_provider.orders
    assert order["student_name"] == "Asha Roy"


def test_amount_is_validated_server_side(client, student_headers, fee):
    too_much = create_order(client, student_headers, fee["id"], amount_paise=150_001)
    assert too_much.status_code == 422
    assert too_much.json()["error"]["code"] == "AMOUNT_EXCEEDS_BALANCE"
    too_small = create_order(client, student_headers, fee["id"], amount_paise=99)
    assert too_small.json()["error"]["code"] == "AMOUNT_TOO_SMALL"
    partial = create_order(client, student_headers, fee["id"], amount_paise=50_000)
    assert partial.status_code == 201 and partial.json()["data"]["amount_paise"] == 50_000


def test_student_cannot_pay_another_students_fee(client, db, student_headers):
    other = make_student(db, name="Other")
    other_fee = make_fee(db, other["id"])
    response = create_order(client, student_headers, other_fee["id"])
    assert response.status_code == 403


def test_open_order_is_reused(client, student_headers, fee):
    first = create_order(client, student_headers, fee["id"]).json()["data"]
    second = create_order(client, student_headers, fee["id"]).json()["data"]
    assert first["provider_order_id"] == second["provider_order_id"]


def test_idempotency_key(client, student_headers, fee):
    headers = {**student_headers, "Idempotency-Key": "order-key-0001"}
    first = create_order(client, headers, fee["id"], amount_paise=60_000).json()["data"]
    replay = create_order(client, headers, fee["id"], amount_paise=60_000).json()["data"]
    assert replay["payment_id"] == first["payment_id"]
    mismatch = create_order(client, headers, fee["id"], amount_paise=70_000)
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_provider_outage_marks_order_failed(client, db, student_headers, fee, payment_provider):
    payment_provider.fail_order_creation = True
    response = create_order(client, student_headers, fee["id"])
    assert response.status_code == 502
    row = one(db, "select status, failure_reason from payments")
    assert (row["status"], row["failure_reason"]) == ("FAILED", "ORDER_CREATION_FAILED")


# ---------------------------------------------------------------------- checkout verification
def test_successful_payment_updates_fee_and_issues_receipt(
    client, db, student_headers, fee, payment_provider, container
):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    response, _ = verify(client, student_headers, payment_provider, order["provider_order_id"])
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["outcome"] == "SUCCEEDED"
    assert data["payment"]["status"] == "SUCCESS"
    assert re.fullmatch(r"BCA-\d{4}-000001", data["receipt"]["receipt_number"])
    assert data["receipt"]["has_pdf"] is True

    fee_now = one(db, "select status, paid_paise from fees where id = %s", fee["id"])
    assert (fee_now["status"], fee_now["paid_paise"]) == ("PAID", 150_000)
    queued = one(db, "select count(*) as n from notifications where template = 'payment_success'")
    assert queued["n"] == 2  # WhatsApp + SMS

    pdf = client.get(f"/api/v1/receipts/{data['receipt']['id']}/download", headers=student_headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


def test_verifying_twice_does_not_double_apply(client, db, student_headers, fee, payment_provider):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    payment = payment_provider.simulate_payment(order["provider_order_id"])
    body = {
        "provider_order_id": order["provider_order_id"],
        "provider_payment_id": payment.payment_id,
        "signature": payment_provider.checkout_signature(
            order["provider_order_id"], payment.payment_id
        ),
    }
    first = client.post("/api/v1/payments/verify", json=body, headers=student_headers)
    second = client.post("/api/v1/payments/verify", json=body, headers=student_headers)
    assert first.json()["data"]["outcome"] == "SUCCEEDED"
    assert second.json()["data"]["outcome"] == "ALREADY_PROCESSED"
    assert second.json()["data"]["receipt"]["id"] == first.json()["data"]["receipt"]["id"]
    assert count(db, "receipts") == 1
    assert one(db, "select paid_paise from fees")["paid_paise"] == 150_000


def test_invalid_checkout_signature_is_rejected(client, db, student_headers, fee, payment_provider):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    response, _ = verify(
        client, student_headers, payment_provider, order["provider_order_id"], signature="0" * 64
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PAYMENT_SIGNATURE"
    assert one(db, "select status from payments")["status"] == "CREATED"
    assert count(db, "receipts") == 0


def test_failed_attempt_then_successful_retry(client, db, student_headers, fee, payment_provider):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    failed, _ = verify(
        client, student_headers, payment_provider, order["provider_order_id"], status="failed"
    )
    assert failed.json()["data"]["outcome"] == "FAILED"
    assert one(db, "select status from fees")["status"] == "PENDING"
    retried, _ = verify(client, student_headers, payment_provider, order["provider_order_id"])
    assert retried.json()["data"]["outcome"] == "SUCCEEDED"


def test_authorized_payment_waits_for_capture_webhook(
    client, db, student_headers, fee, payment_provider
):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    pending, payment = verify(
        client, student_headers, payment_provider, order["provider_order_id"], status="authorized"
    )
    assert pending.json()["data"]["outcome"] == "PENDING"
    assert count(db, "receipts") == 0
    captured = payment_provider.set_payment_status(payment.payment_id, "captured")
    response = webhook(client, payment_provider, "payment.captured", payment=captured)
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "succeeded"
    assert one(db, "select status from payments")["status"] == "SUCCESS"


def test_wrong_amount_is_flagged_and_not_applied(
    client, db, student_headers, fee, payment_provider
):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    response, _ = verify(
        client, student_headers, payment_provider, order["provider_order_id"], amount=100
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "AMOUNT_MISMATCH"
    payment = one(db, "select status, requires_review, review_reason from payments")
    assert payment["status"] == "PENDING" and payment["requires_review"]
    assert payment["review_reason"].startswith("AMOUNT_MISMATCH")
    assert one(db, "select paid_paise from fees")["paid_paise"] == 0
    assert count(db, "receipts") == 0


def test_paid_fee_cannot_be_paid_again(client, student_headers, fee, payment_provider):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    verify(client, student_headers, payment_provider, order["provider_order_id"])
    again = create_order(client, student_headers, fee["id"])
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "FEE_ALREADY_PAID"


# ---------------------------------------------------------------------- webhooks
def test_webhook_with_invalid_signature_is_rejected(client, db, payment_provider):
    response = webhook(client, payment_provider, "payment.captured", signature="f" * 64)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_WEBHOOK_SIGNATURE"
    assert count(db, "payment_events") == 0


def test_webhook_without_signature_is_rejected(client, payment_provider):
    response = client.post("/api/v1/payments/webhooks/razorpay", content=b"{}")
    assert response.status_code == 400


def test_duplicate_webhook_is_processed_once(client, db, student_headers, fee, payment_provider):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    payment = payment_provider.simulate_payment(order["provider_order_id"])
    first = webhook(
        client, payment_provider, "payment.captured", payment=payment, event_id="evt_same0001"
    )
    second = webhook(
        client, payment_provider, "payment.captured", payment=payment, event_id="evt_same0001"
    )
    assert first.json()["data"]["status"] == "succeeded"
    assert second.json()["data"]["status"] == "duplicate"
    assert count(db, "receipts") == 1
    assert one(db, "select paid_paise from fees")["paid_paise"] == 150_000


def test_checkout_then_webhook_is_applied_once(client, db, student_headers, fee, payment_provider):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    _, payment = verify(client, student_headers, payment_provider, order["provider_order_id"])
    late = webhook(client, payment_provider, "order.paid", payment=payment)
    assert late.json()["data"]["status"] == "already_processed"
    assert count(db, "receipts") == 1


def test_webhook_for_unknown_order_is_ignored(client, payment_provider):
    from app.integrations.payments import ProviderPayment

    ghost = ProviderPayment("pay_ghost000001", "order_ghost00001", 100, "INR", "captured")
    response = webhook(client, payment_provider, "payment.captured", payment=ghost)
    assert response.status_code == 200
    assert response.json()["data"] == {"status": "ignored", "detail": "unknown order"}


def test_late_failure_event_never_undoes_success(
    client, db, student_headers, fee, payment_provider
):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    _, payment = verify(client, student_headers, payment_provider, order["provider_order_id"])
    failed = payment_provider.set_payment_status(payment.payment_id, "failed")
    webhook(client, payment_provider, "payment.failed", payment=failed)
    assert one(db, "select status from payments")["status"] == "SUCCESS"


def test_full_refund_reverts_the_fee(client, db, student_headers, fee, payment_provider):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    _, payment = verify(client, student_headers, payment_provider, order["provider_order_id"])
    refund = {"id": "rfnd_test000001", "payment_id": payment.payment_id, "amount": 150_000}
    response = webhook(client, payment_provider, "refund.processed", refund=refund)
    assert response.json()["data"]["status"] == "refunded"
    assert one(db, "select status from payments")["status"] == "REFUNDED"
    fee_now = one(db, "select status, paid_paise from fees")
    assert (fee_now["status"], fee_now["paid_paise"]) == ("PENDING", 0)
    assert count(db, "receipts") == 1  # receipts are never deleted


def test_partial_refund_is_flagged_for_review(client, db, student_headers, fee, payment_provider):
    order = create_order(client, student_headers, fee["id"]).json()["data"]
    _, payment = verify(client, student_headers, payment_provider, order["provider_order_id"])
    refund = {"id": "rfnd_test000002", "payment_id": payment.payment_id, "amount": 50_000}
    response = webhook(client, payment_provider, "refund.processed", refund=refund)
    assert response.json()["data"]["status"] == "review_required"
    row = one(db, "select status, requires_review from payments")
    assert row["status"] == "SUCCESS" and row["requires_review"]


# ---------------------------------------------------------------------- listing and config
def test_payment_config_exposes_only_the_public_key(client, student_headers):
    data = client.get("/api/v1/payments/config", headers=student_headers).json()["data"]
    assert data == {"provider": "MOCK", "key_id": "rzp_mock_key", "currency": "INR"}


def test_students_only_see_their_own_payments(client, db, student_headers, fee, payment_provider):
    create_order(client, student_headers, fee["id"])
    other = make_student(db, name="Other")
    other_headers = auth_header(make_user(db, "STUDENT", student_id=other["id"]))
    assert len(client.get("/api/v1/payments", headers=student_headers).json()["data"]) == 1
    assert client.get("/api/v1/payments", headers=other_headers).json()["data"] == []
    payment_id = client.get("/api/v1/payments", headers=student_headers).json()["data"][0]["id"]
    assert client.get(f"/api/v1/payments/{payment_id}", headers=other_headers).status_code == 403
