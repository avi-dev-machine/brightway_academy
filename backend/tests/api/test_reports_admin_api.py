"""Dashboard, fee reports, CSV exports, first-run setup, settings and account management."""

from datetime import date, timedelta
from uuid import uuid4

from tests.factories import make_fee, make_student, make_user


def offline(client, headers, fee_id, amount):
    return client.post(
        f"/api/v1/fees/{fee_id}/offline-payments",
        json={"amount_paise": amount, "method": "UPI"},
        headers=headers,
    )


def test_dashboard(client, db, admin_headers, course):
    paying = make_student(db, course_id=course["id"])
    make_student(db, status="inactive")
    fee = make_fee(db, paying["id"], amount_paise=100_000)
    make_fee(
        db,
        paying["id"],
        amount_paise=20_000,
        due_date=date.today() - timedelta(days=2),
        status="OVERDUE",
    )
    offline(client, admin_headers, fee["id"], 25_000)

    stats = client.get("/api/v1/reports/dashboard", headers=admin_headers).json()["data"]
    assert (stats["students_active"], stats["students_inactive"], stats["students_total"]) == (
        1,
        1,
        2,
    )
    assert stats["students_by_course"] == [
        {"course_id": str(course["id"]), "course_name": course["name"], "count": 1}
    ]
    assert stats["fees_outstanding_paise"] == 95_000
    assert (stats["fees_overdue_count"], stats["fees_overdue_paise"]) == (1, 20_000)
    assert (stats["collected_today_paise"], stats["payments_today"]) == (25_000, 1)


def test_collections_and_outstanding(client, db, admin_headers, student):
    fee = make_fee(db, student["id"], amount_paise=50_000)
    offline(client, admin_headers, fee["id"], 10_000)
    report = client.get("/api/v1/reports/fees/collections", headers=admin_headers).json()["data"]
    assert report["total_paise"] == 10_000
    assert report["rows"][0]["provider"] == "OFFLINE" and report["rows"][0]["method"] == "UPI"

    outstanding = client.get("/api/v1/reports/fees/outstanding", headers=admin_headers).json()
    assert outstanding["meta"]["total"] == 1
    assert outstanding["data"][0]["outstanding_paise"] == 40_000


def test_csv_exports_neutralise_formulas(client, db, admin_headers):
    make_student(db, id_no="X1", name='=HYPERLINK("http://evil")', contact="+919876543210")
    response = client.get("/api/v1/reports/exports/students.csv", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="students.csv"'
    text = response.content.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("ID No.,Name,Guardian's Name")
    assert "'=HYPERLINK" in text and "'+919876543210" in text

    fees = client.get("/api/v1/reports/exports/fees.csv", headers=admin_headers)
    payments = client.get("/api/v1/reports/exports/payments.csv", headers=admin_headers)
    assert fees.status_code == payments.status_code == 200


def test_setup_flow_and_settings(client, admin_headers):
    status = client.get("/api/v1/admin/setup", headers=admin_headers).json()["data"]
    assert status["admin_exists"] and status["default_id_card_template"]
    assert status["academy_configured"] is False and status["setup_completed"] is False
    assert status["notification_channels_available"] == ["SMS", "WHATSAPP"]

    academy = {
        "name": "Brightway Computer Academy",
        "address": "Main Road, Kolkata",
        "phone": "033 1234 5678",
        "email": "office@brightway.example",
        "student_id_prefix": "BW",
        "receipt_prefix": "BW",
    }
    assert (
        client.put(
            "/api/v1/admin/settings/academy", json=academy, headers=admin_headers
        ).status_code
        == 200
    )
    bad_offsets = client.put(
        "/api/v1/admin/settings/fees", json={"reminder_offsets_days": [500]}, headers=admin_headers
    )
    assert bad_offsets.status_code == 422
    fees = client.put(
        "/api/v1/admin/settings/fees",
        json={"reminder_offsets_days": [7, 0, 0, -2]},
        headers=admin_headers,
    )
    assert fees.json()["data"]["reminder_offsets_days"] == [-2, 0, 7]

    done = client.post("/api/v1/admin/setup/complete", headers=admin_headers).json()["data"]
    assert done["academy_configured"] and done["setup_completed"] and done["completed_at"]

    created = client.post("/api/v1/students", json={"name": "New"}, headers=admin_headers).json()[
        "data"
    ]
    assert created["id_no"] == "BW00001"  # the configured prefix is used

    logs = client.get(
        "/api/v1/admin/audit-logs?entity_type=app_setting", headers=admin_headers
    ).json()["data"]
    assert {log["entity_id"] for log in logs} == {"academy", "fees", "setup"}


def test_system_status_reports_configuration_without_secrets(client, admin_headers):
    response = client.get("/api/v1/admin/system/status", headers=admin_headers)
    data = response.json()["data"]
    assert data["payment_provider"] == "MOCK" and data["storage_backend"] == "local"
    assert data["supabase_admin_configured"] is False
    assert "secret" not in response.text.lower().replace("secret_", "")


def test_link_and_manage_accounts(client, db, admin_headers, admin_id, student):
    user_id = uuid4()
    linked = client.post(
        "/api/v1/admin/users/link",
        json={"user_id": str(user_id), "role": "STUDENT", "student_id": str(student["id"])},
        headers=admin_headers,
    )
    assert linked.status_code == 201, linked.text
    second = client.post(
        "/api/v1/admin/users/link",
        json={"user_id": str(uuid4()), "role": "STUDENT", "student_id": str(student["id"])},
        headers=admin_headers,
    )
    assert second.json()["error"]["code"] == "STUDENT_ACCOUNT_EXISTS"

    inconsistent = client.post(
        "/api/v1/admin/users/link",
        json={"user_id": str(uuid4()), "role": "STUDENT"},
        headers=admin_headers,
    )
    assert inconsistent.status_code == 422

    by_email = client.post(
        "/api/v1/admin/users/link",
        json={"email": "nobody@example.com", "role": "ADMIN"},
        headers=admin_headers,
    )
    assert by_email.json()["error"]["code"] == "AUTH_USER_NOT_FOUND"

    disabled = client.patch(
        f"/api/v1/admin/users/{user_id}", json={"active": False}, headers=admin_headers
    )
    assert disabled.json()["data"]["active"] is False

    self_demote = client.patch(
        f"/api/v1/admin/users/{admin_id}", json={"active": False}, headers=admin_headers
    )
    assert self_demote.status_code == 409

    invite = client.post(
        "/api/v1/admin/users/invite",
        json={"email": "t@example.com", "role": "ADMIN"},
        headers=admin_headers,
    )
    assert invite.status_code == 503  # needs SUPABASE_SERVICE_ROLE_KEY
    users = client.get("/api/v1/admin/users", headers=admin_headers).json()
    assert users["meta"]["total"] == 2


def test_last_admin_cannot_be_removed(client, db, admin_headers):
    other_admin = make_user(db, "ADMIN")
    from tests.factories import auth_header

    # Two admins: the other one may be disabled by the first.
    assert (
        client.patch(
            f"/api/v1/admin/users/{other_admin}", json={"active": False}, headers=admin_headers
        ).status_code
        == 200
    )
    reenabled = client.patch(
        f"/api/v1/admin/users/{other_admin}", json={"active": True}, headers=admin_headers
    )
    assert reenabled.status_code == 200
    # The remaining admin cannot demote themselves even with another active admin around.
    headers = auth_header(other_admin)
    assert (
        client.patch(
            f"/api/v1/admin/users/{other_admin}",
            json={"role": "ADMIN", "active": False},
            headers=headers,
        ).status_code
        == 409
    )
