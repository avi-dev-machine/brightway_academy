"""Student CRUD, search/filter/pagination, photo upload and ID cards."""

from tests.factories import assign_to_batch, image_bytes, make_batch, make_course, make_student


def create(client, headers, **body):
    return client.post("/api/v1/students", json={"name": "Asha Roy", **body}, headers=headers)


def upload_photo(
    client, headers, student_id, data=None, filename="photo.jpg", content_type="image/jpeg"
):
    return client.put(
        f"/api/v1/students/{student_id}/photo",
        files={"photo": (filename, data or image_bytes(), content_type)},
        headers=headers,
    )


def test_create_student_with_generated_id(client, admin_headers, course):
    response = create(
        client,
        admin_headers,
        guardian_name="  Mr   Roy ",
        contact="98765 43210",
        course_id=str(course["id"]),
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["id_no"] == "BCA00001"
    assert data["guardian_name"] == "Mr Roy"  # whitespace normalised
    assert data["contact_e164"] == "+919876543210"
    assert data["course_name"] == "Diploma in Computer Applications"
    assert data["admission_date"] is not None
    assert data["status"] == "active" and data["has_photo"] is False
    assert "photo_path" not in data  # storage paths are never exposed


def test_generated_ids_skip_taken_numbers(client, db, admin_headers):
    make_student(db, id_no="BCA00001")
    assert create(client, admin_headers).json()["data"]["id_no"] == "BCA00002"


def test_duplicate_id_no_is_rejected_ignoring_case(client, admin_headers):
    assert create(client, admin_headers, id_no="BW/2019/07").status_code == 201
    duplicate = create(client, admin_headers, id_no="bw/2019/07")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_STUDENT"


def test_inactive_course_cannot_be_assigned(client, db, admin_headers):
    inactive = make_course(db, active=False)
    response = create(client, admin_headers, course_id=str(inactive["id"]))
    assert response.json()["error"]["code"] == "COURSE_INACTIVE"


def test_get_update_and_deactivate(client, admin_headers, student):
    url = f"/api/v1/students/{student['id']}"
    assert client.get(url, headers=admin_headers).json()["data"]["name"] == "Asha Roy"

    updated = client.patch(
        url, json={"address": "New Town", "contact": "+91 91234 56789"}, headers=admin_headers
    )
    assert updated.json()["data"]["address"] == "New Town"
    assert updated.json()["data"]["contact_e164"] == "+919123456789"

    cleared = client.patch(url, json={"name": None}, headers=admin_headers)
    assert cleared.status_code == 422

    deactivated = client.post(f"{url}/deactivate", headers=admin_headers).json()["data"]
    assert deactivated["status"] == "inactive"
    assert client.get(url, headers=admin_headers).status_code == 200  # still readable
    assert (
        client.post(f"{url}/activate", headers=admin_headers).json()["data"]["status"] == "active"
    )


def test_id_no_can_be_updated_by_admin(client, admin_headers, student):
    response = client.patch(
        f"/api/v1/students/{student['id']}", json={"id_no": "NEW-ID-001"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["id_no"] == "NEW-ID-001"


def test_notify_student_due_fee(client, admin_headers, student):
    response = client.post(
        f"/api/v1/students/{student['id']}/notify-due-fee",
        headers=admin_headers,
        params={"custom_note": "Please pay by Monday"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["student_id"] == str(student["id"])
    assert data["student_name"] == student["name"]
    assert "fee reminder" in data["message_text"]


def test_notify_all_unpaid_students(client, admin_headers):
    response = client.post(
        "/api/v1/students/notify-all-unpaid",
        headers=admin_headers,
        json={"custom_note": "Reminder for all"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "total_unpaid" in data
    assert "queued_count" in data



def test_missing_student(client, admin_headers):
    response = client.get(
        "/api/v1/students/00000000-0000-0000-0000-000000000000", headers=admin_headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "STUDENT_NOT_FOUND"


def test_search_filters_and_pagination(client, db, admin_headers):
    dca = make_course(db, code="DCA", name="DCA")
    tally = make_course(db, code="TALLY", name="Tally")
    for i in range(5):
        make_student(db, id_no=f"S{i}", name=f"Rahul {i}", course_id=dca["id"])
    make_student(db, id_no="S9", name="Priya 100%", course_id=tally["id"], status="inactive")
    batch = make_batch(db, dca["id"])
    assign_to_batch(db, batch["id"], make_student(db, id_no="S10", name="Batch Kid")["id"])

    page = client.get("/api/v1/students?q=rahul&page=2&page_size=2", headers=admin_headers).json()
    assert page["meta"] == {"page": 2, "page_size": 2, "total": 5, "total_pages": 3}
    assert [s["name"] for s in page["data"]] == ["Rahul 2", "Rahul 3"]

    def names(query: str) -> list[str]:
        return [
            s["name"]
            for s in client.get(f"/api/v1/students?{query}", headers=admin_headers).json()["data"]
        ]

    assert len(names(f"course_id={tally['id']}")) == 1
    assert names("status=inactive") == ["Priya 100%"]
    assert names(f"batch_id={batch['id']}") == ["Batch Kid"]
    assert names("q=100%25") == ["Priya 100%"]  # % is matched literally, not as a wildcard
    assert names("q=S1") == ["Batch Kid", "Rahul 1"]  # matches ID No.
    assert client.get("/api/v1/students?page_size=101", headers=admin_headers).status_code == 422


def test_photo_upload_generates_id_card(client, admin_headers, student, container):
    response = upload_photo(client, admin_headers, student["id"])
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id_card_generated"] is True
    assert data["student"]["has_photo"] and data["student"]["has_id_card"]

    photo = client.get(f"/api/v1/students/{student['id']}/photo", headers=admin_headers)
    assert photo.headers["content-type"] == "image/jpeg" and photo.content[:2] == b"\xff\xd8"

    card = client.get(f"/api/v1/id-cards/students/{student['id']}/download", headers=admin_headers)
    assert card.status_code == 200 and card.content.startswith(b"%PDF")

    # A new photo keeps the old file (never destroyed) and regenerates the card.
    upload_photo(client, admin_headers, student["id"], image_bytes("PNG"), "new.png", "image/png")
    history = client.get(
        f"/api/v1/id-cards/students/{student['id']}/history", headers=admin_headers
    )
    assert len(history.json()["data"]) == 2
    stored = list(
        (container.storage._backend._root / "student-photos" / str(student["id"])).glob("*.jpg")
    )  # type: ignore[attr-defined]
    assert len(stored) == 2


def test_invalid_photo_is_rejected(client, admin_headers, student):
    response = upload_photo(client, admin_headers, student["id"], b"not an image")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_IMAGE"
    oversized = upload_photo(client, admin_headers, student["id"], b"\xff" * (5 * 1024 * 1024 + 1))
    assert oversized.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_id_card_without_photo_and_regeneration(client, admin_headers, student):
    generated = client.post(
        f"/api/v1/id-cards/students/{student['id']}/generate", headers=admin_headers
    )
    assert generated.status_code == 201, generated.text
    regenerated = client.post(
        f"/api/v1/id-cards/students/{student['id']}/generate", headers=admin_headers
    )
    assert regenerated.json()["data"]["id"] != generated.json()["data"]["id"]


def test_id_card_templates(client, admin_headers, student):
    layout = {
        "width_mm": 54,
        "height_mm": 85.6,
        "background_color": "#FAFAFA",
        "elements": [
            {
                "type": "text",
                "x": 2,
                "y": 2,
                "w": 50,
                "h": 6,
                "text": "{{academy_name}}",
                "bold": True,
                "align": "C",
            },
            {"type": "image", "x": 15, "y": 10, "w": 24, "h": 30},
            {"type": "text", "x": 2, "y": 45, "w": 50, "h": 5, "text": "{{name}} ({{student_id}})"},
        ],
    }
    created = client.post(
        "/api/v1/id-cards/templates",
        json={"name": "Portrait", "layout": layout, "is_default": True},
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    templates = client.get("/api/v1/id-cards/templates", headers=admin_headers).json()["data"]
    assert [t["name"] for t in templates if t["is_default"]] == ["Portrait"]

    preview = client.get(
        f"/api/v1/id-cards/templates/{created.json()['data']['id']}/preview", headers=admin_headers
    )
    assert preview.content.startswith(b"%PDF")

    bad = client.post(
        "/api/v1/id-cards/templates",
        json={
            "name": "Bad",
            "layout": {**layout, "elements": [{**layout["elements"][0], "text": "{{secret}}"}]},
        },
        headers=admin_headers,
    )
    assert bad.status_code == 422


def test_student_reads_own_record_and_card(client, admin_headers, student, student_headers):
    me = client.get("/api/v1/students/me", headers=student_headers)
    assert me.json()["data"]["id"] == str(student["id"])
    assert (
        client.get(f"/api/v1/students/{student['id']}", headers=student_headers).status_code == 200
    )
    client.post(f"/api/v1/id-cards/students/{student['id']}/generate", headers=admin_headers)
    card = client.get(
        f"/api/v1/id-cards/students/{student['id']}/download", headers=student_headers
    )
    assert card.status_code == 200
