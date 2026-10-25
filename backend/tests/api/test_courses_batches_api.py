"""Courses, teachers, batches and student assignment."""

from tests.factories import auth_header, make_batch, make_student, make_teacher, make_user


def test_course_crud_and_uniqueness(client, admin_headers, student_headers):
    created = client.post(
        "/api/v1/courses",
        json={
            "code": "adca",
            "name": "Advanced Diploma",
            "duration_months": 12,
            "default_fee_paise": 1_200_000,
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    course = created.json()["data"]
    assert course["code"] == "ADCA"

    duplicate_code = client.post(
        "/api/v1/courses", json={"code": "ADCA", "name": "Other"}, headers=admin_headers
    )
    assert duplicate_code.json()["error"]["code"] == "DUPLICATE_COURSE_CODE"
    duplicate_name = client.post(
        "/api/v1/courses", json={"code": "X1", "name": "advanced diploma"}, headers=admin_headers
    )
    assert duplicate_name.json()["error"]["code"] == "DUPLICATE_COURSE_NAME"

    updated = client.patch(
        f"/api/v1/courses/{course['id']}", json={"active": False}, headers=admin_headers
    )
    assert updated.json()["data"]["active"] is False
    # Any signed-in user can read the catalogue; only admins change it.
    assert client.get("/api/v1/courses", headers=student_headers).status_code == 200
    assert (
        client.post(
            "/api/v1/courses", json={"code": "Z", "name": "Z"}, headers=student_headers
        ).status_code
        == 403
    )


def test_teacher_crud(client, admin_headers):
    created = client.post(
        "/api/v1/teachers",
        json={"name": "Ritu Sen", "email": "ritu@example.com"},
        headers=admin_headers,
    )
    assert created.status_code == 201
    duplicate = client.post(
        "/api/v1/teachers",
        json={"name": "Other", "email": "RITU@example.com"},
        headers=admin_headers,
    )
    assert duplicate.json()["error"]["code"] == "DUPLICATE_TEACHER_EMAIL"
    teacher_id = created.json()["data"]["id"]
    patched = client.patch(
        f"/api/v1/teachers/{teacher_id}", json={"phone": "9830012345"}, headers=admin_headers
    )
    assert patched.json()["data"]["phone"] == "9830012345"


def test_batch_lifecycle(client, db, admin_headers, course, teacher):
    created = client.post(
        "/api/v1/batches",
        json={
            "course_id": str(course["id"]),
            "name": "Morning A",
            "teacher_id": str(teacher["id"]),
            "capacity": 2,
            "schedule": "Mon-Fri 8-10am",
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    batch = created.json()["data"]
    assert batch["teacher_name"] == "Ritu Sen" and batch["student_count"] == 0

    s1, s2, s3 = (make_student(db, name=f"S{i}")["id"] for i in range(3))
    added = client.post(
        f"/api/v1/batches/{batch['id']}/students",
        json={"student_ids": [str(s1), str(s2)]},
        headers=admin_headers,
    ).json()["data"]
    assert len(added["added"]) == 2

    again = client.post(
        f"/api/v1/batches/{batch['id']}/students",
        json={"student_ids": [str(s1)]},
        headers=admin_headers,
    ).json()["data"]
    assert again == {"added": [], "already_assigned": [str(s1)]}

    full = client.post(
        f"/api/v1/batches/{batch['id']}/students",
        json={"student_ids": [str(s3)]},
        headers=admin_headers,
    )
    assert full.json()["error"]["code"] == "BATCH_FULL"

    too_small = client.patch(
        f"/api/v1/batches/{batch['id']}", json={"capacity": 1}, headers=admin_headers
    )
    assert too_small.json()["error"]["code"] == "CAPACITY_TOO_LOW"

    removed = client.delete(f"/api/v1/batches/{batch['id']}/students/{s2}", headers=admin_headers)
    assert removed.status_code == 200
    students = client.get(f"/api/v1/batches/{batch['id']}/students", headers=admin_headers).json()[
        "data"
    ]
    assert [s["id"] for s in students] == [str(s1)]


def test_inactive_students_cannot_join_a_batch(client, db, admin_headers, course):
    batch = make_batch(db, course["id"])
    inactive = make_student(db, status="inactive")
    response = client.post(
        f"/api/v1/batches/{batch['id']}/students",
        json={"student_ids": [str(inactive["id"])]},
        headers=admin_headers,
    )
    assert response.json()["error"]["code"] == "STUDENT_INACTIVE"


def test_duplicate_batch_name_in_course(client, db, admin_headers, course):
    make_batch(db, course["id"], name="Evening")
    response = client.post(
        "/api/v1/batches",
        json={"course_id": str(course["id"]), "name": "Evening"},
        headers=admin_headers,
    )
    assert response.json()["error"]["code"] == "DUPLICATE_BATCH_NAME"


def test_teachers_only_see_their_own_batches(client, db, course, teacher, teacher_headers):
    mine = make_batch(db, course["id"], teacher_id=teacher["id"])
    other_teacher = make_teacher(db, name="Other")
    theirs = make_batch(db, course["id"], teacher_id=other_teacher["id"])

    listed = client.get("/api/v1/batches", headers=teacher_headers).json()["data"]
    assert [b["id"] for b in listed] == [str(mine["id"])]
    # Asking for another teacher's batches is silently scoped back to their own.
    scoped = client.get(
        f"/api/v1/batches?teacher_id={other_teacher['id']}", headers=teacher_headers
    ).json()["data"]
    assert [b["id"] for b in scoped] == [str(mine["id"])]
    assert client.get(f"/api/v1/batches/{theirs['id']}", headers=teacher_headers).status_code == 403
    assert (
        client.post(
            "/api/v1/batches",
            json={"course_id": str(course["id"]), "name": "X"},
            headers=teacher_headers,
        ).status_code
        == 403
    )


def test_teacher_profile(client, db, teacher, teacher_headers):
    assert (
        client.get("/api/v1/teachers/me", headers=teacher_headers).json()["data"]["name"]
        == "Ritu Sen"
    )
    admin_only = client.get("/api/v1/teachers", headers=teacher_headers)
    assert admin_only.status_code == 403
    student_headers = auth_header(make_user(db, "STUDENT", student_id=make_student(db)["id"]))
    assert client.get("/api/v1/teachers/me", headers=student_headers).status_code == 403
