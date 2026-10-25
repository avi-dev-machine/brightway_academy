"""End-to-end CSV migration through the API: preview, confirmation policies, idempotency."""

from tests.factories import make_student

HEADER = "ID No.,Name,Guardian's Name,Address,Contact No.,Course\n"
GOOD = (
    "BCA/101,Asha Roy,Mr Roy,Kolkata,9876543210,Diploma in Computer Applications\n"
    "BCA/102,Binod Das,Mrs Das,Howrah,033 2456 7890,DCA\n"
)
BAD = ",Missing Id,G,A,9876543210,DCA\n"


def upload(client, headers, text: str, filename: str = "students.csv"):
    return client.post(
        "/api/v1/imports/students/preview",
        files={"file": (filename, text.encode(), "text/csv")},
        headers=headers,
    )


def student_count(db) -> int:
    with db.transaction() as conn:
        return conn.execute("select count(*) as n from students").fetchone()["n"]


def test_preview_does_not_import(client, admin_headers, db, course):
    response = upload(client, admin_headers, HEADER + GOOD + BAD)
    assert response.status_code == 201, response.text
    job = response.json()["data"]["job"]
    assert job["status"] == "PREVIEWED"
    assert job["summary"]["status_counts"]["ERROR"] == 1
    assert job["summary"]["importable_rows"] == 2
    assert student_count(db) == 0
    problem_rows = response.json()["data"]["problem_rows"]
    assert {r["status"] for r in problem_rows} == {"WARNING", "ERROR"}


def test_strict_policy_refuses_errors_then_skip_errors_imports(client, admin_headers, db, course):
    job_id = upload(client, admin_headers, HEADER + GOOD + BAD).json()["data"]["job"]["id"]

    strict = client.post(f"/api/v1/imports/{job_id}/confirm", json={}, headers=admin_headers)
    assert strict.status_code == 422
    assert strict.json()["error"]["code"] == "IMPORT_HAS_ERRORS"
    assert strict.json()["error"]["details"]["error_rows"] == [4]
    assert student_count(db) == 0

    done = client.post(
        f"/api/v1/imports/{job_id}/confirm",
        json={"error_policy": "SKIP_ERRORS"},
        headers=admin_headers,
    )
    assert done.status_code == 200, done.text
    result = done.json()["data"]["summary"]["result"]
    assert result["imported"] == 2 and result["skipped_errors"] == 1
    assert student_count(db) == 2

    with db.transaction() as conn:
        row = conn.execute("select * from students where id_no = 'BCA/102'").fetchone()
    assert row["contact"] == "033 2456 7890"  # legacy value preserved exactly
    assert row["contact_e164"] is None
    assert row["legacy_course"] == "DCA"
    assert row["course_id"] == course["id"]

    rows = client.get(f"/api/v1/imports/{job_id}/rows", headers=admin_headers).json()["data"]
    assert {r["row_number"]: r["outcome"] for r in rows} == {
        2: "IMPORTED",
        3: "IMPORTED",
        4: "SKIPPED",
    }

    again = client.post(f"/api/v1/imports/{job_id}/confirm", json={}, headers=admin_headers)
    assert again.status_code == 200  # confirming twice is a no-op
    assert student_count(db) == 2


def test_reimporting_the_same_file_is_safe(client, admin_headers, db, course):
    first = upload(client, admin_headers, HEADER + GOOD).json()["data"]["job"]["id"]
    client.post(f"/api/v1/imports/{first}/confirm", json={}, headers=admin_headers)

    second = upload(client, admin_headers, HEADER + GOOD).json()["data"]["job"]
    assert second["summary"]["status_counts"]["EXISTS"] == 2
    assert second["summary"]["previously_imported_job_id"] == first
    done = client.post(f"/api/v1/imports/{second['id']}/confirm", json={}, headers=admin_headers)
    assert done.json()["data"]["summary"]["result"]["imported"] == 0
    assert student_count(db) == 2


def test_existing_students_are_never_overwritten(client, admin_headers, db, course):
    make_student(db, id_no="BCA/101", name="Original Name")
    job_id = upload(client, admin_headers, HEADER + GOOD).json()["data"]["job"]["id"]
    client.post(f"/api/v1/imports/{job_id}/confirm", json={}, headers=admin_headers)
    with db.transaction() as conn:
        name = conn.execute("select name from students where id_no = 'BCA/101'").fetchone()["name"]
    assert name == "Original Name"


def test_unmapped_courses_must_be_resolved(client, admin_headers, db, course):
    text = HEADER + "B1,Asha,G,A,9876543210,Tally Prime\nB2,Binod,G,A,9876543210,Tally Prime\n"
    job_id = upload(client, admin_headers, text).json()["data"]["job"]["id"]

    refused = client.post(f"/api/v1/imports/{job_id}/confirm", json={}, headers=admin_headers)
    assert refused.status_code == 422
    assert refused.json()["error"]["details"]["unmapped_courses"] == ["Tally Prime"]

    mapped = client.post(
        f"/api/v1/imports/{job_id}/confirm",
        json={"course_mapping": {"tally prime": str(course["id"])}},
        headers=admin_headers,
    )
    assert mapped.status_code == 200, mapped.text
    with db.transaction() as conn:
        ids = {r["course_id"] for r in conn.execute("select course_id from students").fetchall()}
    assert ids == {course["id"]}


def test_missing_courses_can_be_created(client, admin_headers, db):
    job_id = upload(client, admin_headers, HEADER + "B1,Asha,G,A,9876543210,Tally Prime\n").json()[
        "data"
    ]["job"]["id"]
    done = client.post(
        f"/api/v1/imports/{job_id}/confirm",
        json={"create_missing_courses": True},
        headers=admin_headers,
    )
    assert done.json()["data"]["summary"]["result"]["courses_created"] == ["Tally Prime"]
    courses = client.get("/api/v1/courses", headers=admin_headers).json()["data"]
    assert [(c["code"], c["name"]) for c in courses] == [("TALLY-PRIME", "Tally Prime")]


def test_invalid_files_are_rejected(client, admin_headers):
    wrong_header = upload(client, admin_headers, "Name,Phone\nAsha,1\n")
    assert wrong_header.json()["error"]["code"] == "MISSING_COLUMNS"
    not_csv = upload(client, admin_headers, HEADER, filename="students.xlsx")
    assert not_csv.json()["error"]["code"] == "INVALID_FILE_EXTENSION"
    no_rows = upload(client, admin_headers, HEADER)
    assert no_rows.json()["error"]["code"] == "NO_DATA_ROWS"


def test_import_requires_admin(client, teacher_headers, student_headers):
    for headers in (teacher_headers, student_headers):
        assert upload(client, headers, HEADER + GOOD).status_code == 403
