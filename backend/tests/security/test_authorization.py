"""Authorization: roles, resource ownership (IDOR) and unauthenticated access."""

import jwt
import pytest

from tests.factories import (
    TEST_ISSUER,
    assign_to_batch,
    auth_header,
    make_batch,
    make_fee,
    make_student,
    make_user,
)

ADMIN_ONLY = [
    ("GET", "/api/v1/reports/dashboard"),
    ("GET", "/api/v1/reports/exports/students.csv"),
    ("GET", "/api/v1/admin/users"),
    ("GET", "/api/v1/admin/audit-logs"),
    ("GET", "/api/v1/admin/system/status"),
    ("PUT", "/api/v1/admin/settings/academy"),
    ("GET", "/api/v1/imports"),
    ("GET", "/api/v1/notifications"),
    ("GET", "/api/v1/fees/plans"),
    ("POST", "/api/v1/students"),
    ("GET", "/api/v1/teachers"),
    ("GET", "/api/v1/id-cards/templates"),
]

PROTECTED = [
    *ADMIN_ONLY,
    ("GET", "/api/v1/students"),
    ("GET", "/api/v1/fees"),
    ("GET", "/api/v1/payments"),
    ("GET", "/api/v1/receipts"),
    ("GET", "/api/v1/auth/me"),
    ("GET", "/api/v1/courses"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_unauthenticated_requests_are_rejected(client, method, path):
    response = client.request(method, path, json={})
    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path"), ADMIN_ONLY)
def test_teachers_cannot_use_admin_endpoints(client, teacher_headers, method, path):
    assert client.request(method, path, json={}, headers=teacher_headers).status_code in (403, 422)
    assert client.request(method, path, headers=teacher_headers).status_code != 200


@pytest.mark.parametrize(("method", "path"), ADMIN_ONLY)
def test_students_cannot_use_admin_endpoints(client, student_headers, method, path):
    assert client.request(method, path, headers=student_headers).status_code != 200


def test_student_cannot_read_another_student(client, db, student_headers):
    other = make_student(db, name="Other")
    for path in (
        f"/api/v1/students/{other['id']}",
        f"/api/v1/students/{other['id']}/photo",
        f"/api/v1/id-cards/students/{other['id']}/download",
        f"/api/v1/attendance/students/{other['id']}",
        f"/api/v1/fees/students/{other['id']}/summary",
    ):
        assert client.get(path, headers=student_headers).status_code == 403, path
    assert client.get("/api/v1/students", headers=student_headers).status_code == 403


def test_student_cannot_read_another_students_receipt(client, db, admin_headers, student_headers):
    other = make_student(db, name="Other")
    fee = make_fee(db, other["id"])
    receipt = client.post(
        f"/api/v1/fees/{fee['id']}/offline-payments",
        json={"amount_paise": 500, "method": "CASH"},
        headers=admin_headers,
    ).json()["data"]["receipt"]
    assert (
        client.get(f"/api/v1/receipts/{receipt['id']}", headers=student_headers).status_code == 403
    )
    assert (
        client.get(
            f"/api/v1/receipts/{receipt['id']}/download", headers=student_headers
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/receipts?student_id={other['id']}", headers=student_headers
        ).status_code
        == 403
    )
    assert client.get("/api/v1/receipts", headers=student_headers).json()["data"] == []


def test_teacher_sees_only_assigned_students(client, db, course, teacher, teacher_headers):
    batch = make_batch(db, course["id"], teacher_id=teacher["id"])
    mine = make_student(db, name="Mine")
    assign_to_batch(db, batch["id"], mine["id"])
    not_mine = make_student(db, name="Not Mine")

    listed = client.get("/api/v1/students", headers=teacher_headers).json()["data"]
    assert [s["name"] for s in listed] == ["Mine"]
    assert client.get(f"/api/v1/students/{mine['id']}", headers=teacher_headers).status_code == 200
    assert (
        client.get(f"/api/v1/students/{not_mine['id']}", headers=teacher_headers).status_code == 403
    )
    assert (
        client.patch(
            f"/api/v1/students/{mine['id']}", json={"name": "X"}, headers=teacher_headers
        ).status_code
        == 403
    )


def test_disabling_an_account_revokes_access_immediately(client, db, admin_headers, student):
    user_id = make_user(db, "STUDENT", student_id=student["id"])
    headers = auth_header(user_id)
    assert client.get("/api/v1/students/me", headers=headers).status_code == 200
    client.patch(f"/api/v1/admin/users/{user_id}", json={"active": False}, headers=admin_headers)
    assert client.get("/api/v1/students/me", headers=headers).status_code == 403


def test_forged_hs256_token_is_rejected(client, admin_id):
    forged = jwt.encode(
        {
            "sub": str(admin_id),
            "aud": "authenticated",
            "iss": TEST_ISSUER,
            "role": "authenticated",
            "iat": 1,
            "exp": 4_102_444_800,
        },
        "sb_publishable_test",  # attacker tries the public key as an HMAC secret
        algorithm="HS256",
    )
    response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_role_in_token_metadata_is_ignored(client, db, student):
    # Roles come from user_profiles, never from user-editable token claims.
    from tests.factories import make_token

    user_id = make_user(db, "STUDENT", student_id=student["id"])
    token = make_token(user_id, user_metadata={"role": "ADMIN"}, app_role="ADMIN")
    response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_errors_do_not_leak_internals(client, admin_headers):
    response = client.get("/api/v1/students/not-a-uuid", headers=admin_headers)
    assert response.status_code == 422
    body = response.text.lower()
    assert "traceback" not in body and "psycopg" not in body and "postgresql://" not in body
