"""Concurrent import confirmations that both auto-create the same course."""

import threading

from app.core.constants import Role
from app.core.permissions import CurrentUser
from app.dependencies import csv_import_service
from app.schemas.import_job import ImportConfirmRequest

HEADER = "ID No.,Name,Guardian's Name,Address,Contact No.,Course\n"


def test_concurrent_confirms_create_the_course_once(container, db, admin_id):
    service = csv_import_service(container)
    admin = CurrentUser(user_id=admin_id, role=Role.ADMIN)
    jobs = [
        service.preview(
            admin,
            filename=f"part{i}.csv",
            content_type="text/csv",
            data=(HEADER + f"P{i},Student {i},G,A,9876543210,Tally Prime\n").encode(),
        ).job.id
        for i in range(2)
    ]
    errors: list[Exception] = []
    barrier = threading.Barrier(2)

    def confirm(job_id):
        try:
            barrier.wait()
            service.confirm(admin, job_id, ImportConfirmRequest(create_missing_courses=True))
        except Exception as exc:  # collected and asserted below
            errors.append(exc)

    threads = [threading.Thread(target=confirm, args=(job_id,)) for job_id in jobs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert errors == []
    with db.transaction() as conn:
        courses = conn.execute("select id from courses where name = 'Tally Prime'").fetchall()
        students = conn.execute("select course_id from students").fetchall()
    assert len(courses) == 1
    assert {s["course_id"] for s in students} == {courses[0]["id"]}
