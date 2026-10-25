"""Fee plans, installments, balances, concessions, offline payments and cancellation."""

from datetime import date, timedelta

import pytest

from tests.factories import auth_header, make_fee, make_student, make_user


def one(db, query, *params):
    with db.transaction() as conn:
        return conn.execute(query, params).fetchone()


@pytest.fixture
def plan(client, admin_headers, course):
    response = client.post(
        "/api/v1/fees/plans",
        json={
            "name": "DCA 3 installments",
            "course_id": str(course["id"]),
            "plan_type": "INSTALLMENT",
            "amount_paise": 1_000_000,
            "installment_count": 3,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def offline(client, headers, fee_id, amount, **extra):
    return client.post(
        f"/api/v1/fees/{fee_id}/offline-payments",
        json={"amount_paise": amount, "method": "CASH", **extra},
        headers=headers,
    )


def test_assign_installment_plan(client, admin_headers, student, plan):
    start = date.today() + timedelta(days=5)
    response = client.post(
        f"/api/v1/fees/students/{student['id']}/assign-plan",
        json={"fee_plan_id": plan["id"], "start_date": start.isoformat()},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    fees = response.json()["data"]
    assert [f["amount_paise"] for f in fees] == [333_333, 333_333, 333_334]
    assert [f["installment_no"] for f in fees] == [1, 2, 3]
    assert all(f["status"] == "PENDING" and f["balance_paise"] == f["amount_paise"] for f in fees)

    again = client.post(
        f"/api/v1/fees/students/{student['id']}/assign-plan",
        json={"fee_plan_id": plan["id"], "start_date": start.isoformat()},
        headers=admin_headers,
    )
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "FEE_PLAN_ALREADY_ASSIGNED"


def test_plan_starting_in_the_past_is_overdue(client, admin_headers, student, plan):
    start = date.today() - timedelta(days=40)
    fees = client.post(
        f"/api/v1/fees/students/{student['id']}/assign-plan",
        json={"fee_plan_id": plan["id"], "start_date": start.isoformat()},
        headers=admin_headers,
    ).json()["data"]
    assert fees[0]["status"] == "OVERDUE"


def test_cannot_assign_fees_to_inactive_student(client, db, admin_headers, plan):
    inactive = make_student(db, status="inactive")
    response = client.post(
        f"/api/v1/fees/students/{inactive['id']}/assign-plan",
        json={"fee_plan_id": plan["id"], "start_date": date.today().isoformat()},
        headers=admin_headers,
    )
    assert response.json()["error"]["code"] == "STUDENT_INACTIVE"


def test_concessions(client, db, admin_headers, student):
    fee = make_fee(db, student["id"], amount_paise=100_000)
    partial = client.post(
        f"/api/v1/fees/{fee['id']}/concessions",
        json={"amount_paise": 20_000, "reason": "Sibling discount"},
        headers=admin_headers,
    ).json()["data"]
    assert partial["balance_paise"] == 80_000 and partial["status"] == "PENDING"

    too_much = client.post(
        f"/api/v1/fees/{fee['id']}/concessions",
        json={"amount_paise": 80_001, "reason": "Too much"},
        headers=admin_headers,
    )
    assert too_much.json()["error"]["code"] == "CONCESSION_EXCEEDS_BALANCE"

    full = client.post(
        f"/api/v1/fees/{fee['id']}/concessions",
        json={"amount_paise": 80_000, "reason": "Scholarship"},
        headers=admin_headers,
    ).json()["data"]
    assert full["status"] == "PAID"
    assert full["concession_reason"] == "Sibling discount; Scholarship"


def test_partial_then_full_offline_payment(client, db, admin_headers, student):
    fee = make_fee(db, student["id"], amount_paise=100_000)
    first = offline(client, admin_headers, fee["id"], 40_000, reference="Counter 1")
    assert first.status_code == 201, first.text
    data = first.json()["data"]
    assert data["payment"]["provider"] == "OFFLINE" and data["payment"]["method"] == "CASH"
    assert data["receipt"]["amount_paise"] == 40_000
    assert one(db, "select status from fees")["status"] == "PARTIALLY_PAID"

    overpay = offline(client, admin_headers, fee["id"], 60_001)
    assert overpay.json()["error"]["code"] == "AMOUNT_EXCEEDS_BALANCE"

    offline(client, admin_headers, fee["id"], 60_000)
    fee_now = one(db, "select status, paid_paise from fees")
    assert (fee_now["status"], fee_now["paid_paise"]) == ("PAID", 100_000)
    assert one(db, "select count(*) as n from receipts")["n"] == 2

    already = offline(client, admin_headers, fee["id"], 1)
    assert already.json()["error"]["code"] == "FEE_ALREADY_PAID"


def test_offline_payment_idempotency(client, db, admin_headers, student):
    fee = make_fee(db, student["id"], amount_paise=100_000)
    first = offline(
        client, admin_headers, fee["id"], 30_000, idempotency_key="cash-entry-0001"
    ).json()["data"]
    replay = offline(
        client, admin_headers, fee["id"], 30_000, idempotency_key="cash-entry-0001"
    ).json()["data"]
    assert replay["outcome"] == "ALREADY_PROCESSED"
    assert replay["payment"]["id"] == first["payment"]["id"]
    assert one(db, "select paid_paise from fees")["paid_paise"] == 30_000
    conflict = offline(client, admin_headers, fee["id"], 31_000, idempotency_key="cash-entry-0001")
    assert conflict.status_code == 409


def test_offline_payment_date_cannot_be_in_the_future(client, db, admin_headers, student):
    fee = make_fee(db, student["id"])
    tomorrow = (date.today() + timedelta(days=2)).isoformat()
    assert (
        offline(client, admin_headers, fee["id"], 100, paid_on=tomorrow).json()["error"]["code"]
        == "FUTURE_DATE"
    )


def test_cancel_fee(client, db, admin_headers, student):
    unpaid = make_fee(db, student["id"])
    cancelled = client.post(
        f"/api/v1/fees/{unpaid['id']}/cancel",
        json={"reason": "Course changed"},
        headers=admin_headers,
    ).json()["data"]
    assert cancelled["status"] == "CANCELLED"

    paid = make_fee(db, student["id"], amount_paise=10_000)
    offline(client, admin_headers, paid["id"], 5_000)
    refused = client.post(
        f"/api/v1/fees/{paid['id']}/cancel",
        json={"reason": "Course changed"},
        headers=admin_headers,
    )
    assert refused.json()["error"]["code"] == "FEE_HAS_PAYMENTS"


def test_fee_summary_and_student_scoping(client, db, admin_headers, student, student_headers):
    make_fee(db, student["id"], amount_paise=50_000)
    make_fee(
        db,
        student["id"],
        amount_paise=30_000,
        due_date=date.today() - timedelta(days=3),
        status="OVERDUE",
    )
    summary = client.get(
        f"/api/v1/fees/students/{student['id']}/summary", headers=student_headers
    ).json()["data"]
    assert summary["total_outstanding_paise"] == 80_000
    assert summary["overdue_count"] == 1 and summary["overdue_paise"] == 30_000

    own = client.get("/api/v1/fees", headers=student_headers).json()
    assert own["meta"]["total"] == 2

    other = make_student(db, name="Other")
    other_fee = make_fee(db, other["id"])
    assert client.get(f"/api/v1/fees/{other_fee['id']}", headers=student_headers).status_code == 403
    assert (
        client.get(
            f"/api/v1/fees/students/{other['id']}/summary", headers=student_headers
        ).status_code
        == 403
    )
    assert (
        client.get(f"/api/v1/fees?student_id={other['id']}", headers=student_headers).status_code
        == 403
    )


def test_mark_overdue(container, db, student):
    from app.dependencies import fee_service

    make_fee(db, student["id"], due_date=date.today() - timedelta(days=1))
    make_fee(db, student["id"], due_date=date.today() + timedelta(days=1))
    assert fee_service(container).mark_overdue() == 1
    assert fee_service(container).mark_overdue() == 0


def test_teacher_cannot_manage_fees(client, db, teacher_headers, student):
    fee = make_fee(db, student["id"])
    assert client.get("/api/v1/fees", headers=teacher_headers).status_code == 403
    assert offline(client, teacher_headers, fee["id"], 100).status_code == 403
    assert client.get("/api/v1/fees/plans", headers=teacher_headers).status_code == 403


def test_audit_log_records_offline_payment(client, db, admin_headers, admin_id, student):
    fee = make_fee(db, student["id"])
    offline(client, admin_headers, fee["id"], 1_000)
    logs = client.get(
        "/api/v1/admin/audit-logs?action=payment.succeeded", headers=admin_headers
    ).json()["data"]
    assert len(logs) == 1 and logs[0]["actor_user_id"] == str(admin_id)
    assert logs[0]["before"]["status"] == "CREATED" and logs[0]["after"]["status"] == "SUCCESS"


def test_unrelated_student_token_cannot_record_payment(client, db, student):
    fee = make_fee(db, student["id"])
    headers = auth_header(make_user(db, "STUDENT", student_id=student["id"]))
    assert offline(client, headers, fee["id"], 100).status_code == 403
