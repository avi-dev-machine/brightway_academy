"""Attendance marking, teacher access and reports."""

from datetime import date, timedelta

import pytest

from tests.factories import assign_to_batch, make_batch, make_student, make_teacher

TODAY = date.today()


@pytest.fixture
def batch(db, course, teacher, student):
    batch = make_batch(db, course["id"], teacher_id=teacher["id"])
    assign_to_batch(db, batch["id"], student["id"])
    return batch


def mark(client, headers, batch_id, records, day=TODAY):
    return client.post(
        f"/api/v1/attendance/batches/{batch_id}",
        json={"attendance_date": day.isoformat(), "records": records},
        headers=headers,
    )


def test_teacher_marks_and_updates_attendance(client, batch, student, teacher_headers):
    first = mark(
        client,
        teacher_headers,
        batch["id"],
        [{"student_id": str(student["id"]), "status": "ABSENT"}],
    )
    assert first.status_code == 200, first.text
    second = mark(
        client,
        teacher_headers,
        batch["id"],
        [{"student_id": str(student["id"]), "status": "LATE", "remarks": "Bus delay"}],
    )
    assert second.json()["data"][0]["id"] == first.json()["data"][0]["id"]  # same day is updated
    roster = client.get(
        f"/api/v1/attendance/batches/{batch['id']}", headers=teacher_headers
    ).json()["data"]
    assert roster == [
        {
            "student_id": str(student["id"]),
            "id_no": "BCA-001",
            "name": "Asha Roy",
            "status": "LATE",
            "remarks": "Bus delay",
        }
    ]


def test_teacher_cannot_mark_another_teachers_batch(client, db, course, student, teacher_headers):
    other = make_batch(db, course["id"], teacher_id=make_teacher(db, name="Other")["id"])
    assign_to_batch(db, other["id"], student["id"])
    response = mark(
        client,
        teacher_headers,
        other["id"],
        [{"student_id": str(student["id"]), "status": "PRESENT"}],
    )
    assert response.status_code == 403


def test_only_batch_members_can_be_marked(client, db, batch, teacher_headers):
    outsider = make_student(db, name="Outsider")
    response = mark(
        client,
        teacher_headers,
        batch["id"],
        [{"student_id": str(outsider["id"]), "status": "PRESENT"}],
    )
    assert response.json()["error"]["code"] == "STUDENT_NOT_IN_BATCH"


def test_future_dates_and_duplicates_are_rejected(client, batch, student, teacher_headers):
    record = {"student_id": str(student["id"]), "status": "PRESENT"}
    future = mark(client, teacher_headers, batch["id"], [record], TODAY + timedelta(days=1))
    assert future.json()["error"]["code"] == "FUTURE_DATE"
    duplicate = mark(client, teacher_headers, batch["id"], [record, record])
    assert duplicate.status_code == 422


def test_reports_and_student_view(client, db, batch, student, teacher_headers, student_headers):
    for offset, status in ((0, "PRESENT"), (1, "LATE"), (2, "ABSENT"), (3, "EXCUSED")):
        mark(
            client,
            teacher_headers,
            batch["id"],
            [{"student_id": str(student["id"]), "status": status}],
            TODAY - timedelta(days=offset),
        )

    report = client.get(
        f"/api/v1/attendance/batches/{batch['id']}/report", headers=teacher_headers
    ).json()["data"]
    assert report[0]["present"] == 1 and report[0]["late"] == 1 and report[0]["absent"] == 1
    assert report[0]["percentage"] == 66.7  # excused days are not counted

    own = client.get(
        f"/api/v1/attendance/students/{student['id']}", headers=student_headers
    ).json()["data"]
    assert own["summary"]["total"] == 4 and len(own["records"]) == 4

    other = make_student(db, name="Other")
    assert (
        client.get(
            f"/api/v1/attendance/students/{other['id']}", headers=student_headers
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/attendance/students/{other['id']}", headers=teacher_headers
        ).status_code
        == 403
    )


def test_students_cannot_mark_attendance(client, batch, student, student_headers):
    response = mark(
        client,
        student_headers,
        batch["id"],
        [{"student_id": str(student["id"]), "status": "PRESENT"}],
    )
    assert response.status_code == 403


def test_invalid_range(client, batch, teacher_headers):
    response = client.get(
        f"/api/v1/attendance/batches/{batch['id']}/report?date_from=2026-02-01&date_to=2026-01-01",
        headers=teacher_headers,
    )
    assert response.json()["error"]["code"] == "INVALID_RANGE"
