"""Student records: create, read, search, update, deactivate and photographs."""

import logging
from urllib.parse import quote_plus
from uuid import UUID, uuid4

from app.core.passwords import hash_password
from app.core.permissions import CurrentUser, ensure_student_access
from app.db.client import Database, DbConnection
from app.db.transactions import translate_constraint_errors
from app.exceptions import (
    AppError,
    DuplicateStudentError,
    ForbiddenError,
    NotFoundError,
    StudentNotFoundError,
    ValidationFailedError,
)
from app.integrations.storage.service import StorageService
from app.models.notification import NotificationTemplate
from app.models.student import Student, StudentMonthlyFee, StudentStatus
from app.repositories.course_repository import CourseRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.student import (
    BroadcastDueNoticeResult,
    DueFeeNoticeResult,
    StudentCreate,
    StudentPhotoResult,
    StudentUpdate,
)
from app.services.audit_service import record_audit
from app.services.id_card_service import IdCardService
from app.services.notification_service import NotificationService
from app.services.settings_service import load_academy
from app.utils.dates import local_today
from app.utils.file_validation import validate_image
from app.utils.id_generator import generate_student_id
from app.utils.pagination import Page, PageParams
from app.utils.pdf import format_inr
from app.utils.validators import normalize_indian_phone

logger = logging.getLogger(__name__)

_CONSTRAINTS = {
    "students_id_no_key": DuplicateStudentError,
    "students_id_no_lower_key": DuplicateStudentError,
}


class StudentService:
    def __init__(
        self,
        db: Database,
        storage: StorageService,
        id_cards: IdCardService,
        *,
        max_photo_bytes: int,
        timezone: str,
    ) -> None:
        self.db = db
        self.storage = storage
        self.id_cards = id_cards
        self.max_photo_bytes = max_photo_bytes
        self.timezone = timezone

    def search(
        self,
        user: CurrentUser,
        *,
        q: str | None = None,
        course_id: UUID | None = None,
        batch_id: UUID | None = None,
        status: StudentStatus | None = None,
        program: str | None = None,
        has_id: bool | None = None,
        fee_status: str | None = None,
        params: PageParams,
    ) -> Page[Student]:
        if user.is_student:
            raise ForbiddenError("Students can only view their own record.")
        with self.db.transaction() as conn:
            rows, total = StudentRepository(conn).search(
                q=q,
                course_id=course_id,
                batch_id=batch_id,
                status=status.value if status else None,
                program=program,
                has_id=has_id,
                fee_status=fee_status,
                teacher_id=user.teacher_id if user.is_teacher else None,
                limit=params.limit,
                offset=params.offset,
            )
        return Page([Student.model_validate(r) for r in rows], total, params)

    def get(self, user: CurrentUser, student_id: UUID) -> Student:
        with self.db.transaction() as conn:
            ensure_student_access(conn, user, student_id)
            row = StudentRepository(conn).get(student_id)
        if row is None:
            raise StudentNotFoundError()
        return Student.model_validate(row)

    def get_own(self, user: CurrentUser) -> Student:
        if not user.is_student or user.student_id is None:
            raise ForbiddenError()
        return self.get(user, user.student_id)

    def get_monthly_fees(self, user: CurrentUser, student_id: UUID) -> list[StudentMonthlyFee]:
        with self.db.transaction() as conn:
            ensure_student_access(conn, user, student_id)
            rows = StudentRepository(conn).get_monthly_fees(student_id)
        return [StudentMonthlyFee.model_validate(r) for r in rows]

    def create(self, actor: CurrentUser, payload: StudentCreate) -> Student:
        with self.db.transaction() as conn:
            repo = StudentRepository(conn)
            self._check_course(conn, payload.course_id)
            id_no = payload.id_no
            if id_no is None:
                prefix = load_academy(conn).student_id_prefix
                id_no = generate_student_id(prefix, repo.next_sequence_value, repo.id_no_exists)
            elif repo.id_no_exists(id_no):
                raise DuplicateStudentError()
            with translate_constraint_errors(_CONSTRAINTS):
                inserted = repo.insert(
                    {
                        "id_no": id_no,
                        "name": payload.name,
                        "guardian_name": payload.guardian_name,
                        "address": payload.address,
                        "contact": payload.contact,
                        "contact_e164": normalize_indian_phone(payload.contact),
                        "course_id": payload.course_id,
                        "admission_date": payload.admission_date or local_today(self.timezone),
                    }
                )
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="student.created",
                entity_type="student",
                entity_id=inserted["id"],
                after=inserted,
            )
            row = repo.get(inserted["id"])
        return Student.model_validate(row)

    def update(self, actor: CurrentUser, student_id: UUID, payload: StudentUpdate) -> Student:
        changes = payload.model_dump(exclude_unset=True)
        with self.db.transaction() as conn:
            repo = StudentRepository(conn)
            current = repo.lock(student_id)
            if current is None:
                raise StudentNotFoundError()
            if "course_id" in changes:
                self._check_course(conn, changes["course_id"])
            if "contact" in changes:
                changes["contact_e164"] = normalize_indian_phone(changes["contact"])
            if "id_no" in changes:
                new_id = changes["id_no"]
                if new_id:
                    new_id = new_id.strip()
                    changes["id_no"] = new_id
                    existing = repo.get_by_id_no(new_id)
                    if existing and existing["id"] != student_id:
                        raise DuplicateStudentError("A student with this ID number already exists.")
                else:
                    changes["id_no"] = None
            if "program" in changes and changes["program"] is not None:
                changes["program"] = changes["program"].strip().upper()
                if changes["program"] not in ("CERTIFICATE", "NON_CERTIFICATE"):
                    raise ValidationFailedError("Invalid program type.")

            with translate_constraint_errors(_CONSTRAINTS):
                updated = repo.update_fields(student_id, changes)

            if "id_no" in changes or "initial_passcode" in changes:
                user_repo = UserRepository(conn)
                user_row = conn.execute(
                    "select user_id from user_profiles where student_id = %s", (student_id,)
                ).fetchone()
                if user_row:
                    user_updates = {}
                    if changes.get("id_no"):
                        user_updates["identifier"] = changes["id_no"]
                    if changes.get("initial_passcode"):
                        user_updates["password_hash"] = hash_password(changes["initial_passcode"])
                    if user_updates:
                        user_repo.update(user_row["user_id"], user_updates)

            record_audit(
                conn,
                actor_id=actor.user_id,
                action="student.updated",
                entity_type="student",
                entity_id=student_id,
                before=current,
                after=updated,
            )
            row = repo.get(student_id)
        return Student.model_validate(row)

    def notify_due_fee(
        self,
        actor: CurrentUser,
        student_id: UUID,
        notifications: NotificationService,
        custom_note: str | None = None,
    ) -> DueFeeNoticeResult:
        with self.db.transaction() as conn:
            repo = StudentRepository(conn)
            student_row = repo.get(student_id)
            if student_row is None:
                raise StudentNotFoundError()
            academy = load_academy(conn)

        student_name = student_row["name"]
        id_no = student_row["id_no"] or "Pending"
        raw_contact = student_row.get("contact") or ""
        contact_e164 = student_row.get("contact_e164") or normalize_indian_phone(raw_contact)
        total_due_paise = student_row.get("total_due_paise") or 0
        unpaid_months = student_row.get("unpaid_months") or []
        course_name = (
            student_row.get("course_name") or student_row.get("legacy_course") or "General"
        )

        if total_due_paise == 0:
            rate = student_row.get("monthly_fee_paise") or 40000
            total_due_paise = rate * max(len(unpaid_months), 1)

        amount_formatted = format_inr(total_due_paise)
        months_str = ", ".join(unpaid_months) if unpaid_months else "Current Session"

        note_part = (
            f"\nNote: {custom_note.strip()}\n" if custom_note and custom_note.strip() else ""
        )
        message_text = (
            f"Dear {student_name},\n\n"
            f"This is a gentle fee reminder from {academy.name}.\n\n"
            f"• Student ID: {id_no}\n"
            f"• Course: {course_name}\n"
            f"• Due Period: {months_str}\n"
            f"• Total Due Amount: {amount_formatted}\n"
            f"{note_part}\n"
            f"Kindly clear the fee dues at the academy office or via online payment.\n\n"
            f"Thank you,\n{academy.name}"
        )

        clean_phone = ""
        whatsapp_url = None
        if contact_e164:
            clean_phone = contact_e164.lstrip("+")
            whatsapp_url = f"https://wa.me/{clean_phone}?text={quote_plus(message_text)}"

        notification_id = None
        queued = False
        if contact_e164:
            with self.db.transaction() as conn:
                notif_repo = NotificationRepository(conn)
                today_str = local_today(self.timezone).isoformat()
                enqueued = notif_repo.enqueue(
                    student_id=student_id,
                    fee_id=None,
                    payment_id=None,
                    channel="WHATSAPP",
                    recipient=contact_e164,
                    template=NotificationTemplate.FEE_REMINDER.value,
                    payload={
                        "name": student_name,
                        "fee_title": f"Monthly Dues ({months_str})",
                        "amount": amount_formatted,
                        "due_date": "Immediate",
                        "academy_name": academy.name,
                    },
                    dedupe_key=f"manual_fee_notice:{student_id}:{today_str}:{uuid4().hex[:8]}",
                )
                if enqueued:
                    notification_id = enqueued["id"]
                    queued = True
                record_audit(
                    conn,
                    actor_id=actor.user_id,
                    action="student.fee_reminder_notified",
                    entity_type="student",
                    entity_id=student_id,
                    after={"recipient": contact_e164, "amount_paise": total_due_paise},
                )
            try:
                notifications.process_due(batch_size=10)
            except Exception as e:
                logger.warning("Error processing notification queue: %s", e)

        return DueFeeNoticeResult(
            student_id=student_id,
            student_name=student_name,
            contact=raw_contact,
            contact_e164=contact_e164,
            amount_paise=total_due_paise,
            amount_formatted=amount_formatted,
            unpaid_months=unpaid_months,
            message_text=message_text,
            whatsapp_url=whatsapp_url,
            queued=queued,
            notification_id=notification_id,
        )

    def notify_all_unpaid(
        self,
        actor: CurrentUser,
        notifications: NotificationService,
        *,
        program: str | None = None,
        course_id: UUID | None = None,
        custom_note: str | None = None,
    ) -> BroadcastDueNoticeResult:
        with self.db.transaction() as conn:
            repo = StudentRepository(conn)
            unpaid_students = repo.get_unpaid_students(program=program, course_id=course_id)
            academy = load_academy(conn)

        total_unpaid = len(unpaid_students)
        queued_count = 0
        skipped_no_contact = 0
        notified: list[DueFeeNoticeResult] = []
        today_str = local_today(self.timezone).isoformat()

        for student in unpaid_students:
            student_id = student["id"]
            student_name = student["name"]
            id_no = student["id_no"] or "Pending"
            raw_contact = student.get("contact") or ""
            contact_e164 = student.get("contact_e164") or normalize_indian_phone(raw_contact)
            total_due_paise = student.get("total_due_paise") or 0
            unpaid_months = student.get("unpaid_months") or []
            course_name = student.get("course_name") or student.get("legacy_course") or "General"

            if total_due_paise == 0:
                rate = student.get("monthly_fee_paise") or 40000
                total_due_paise = rate * max(len(unpaid_months), 1)

            amount_formatted = format_inr(total_due_paise)
            months_str = ", ".join(unpaid_months) if unpaid_months else "Current Session"

            note_part = (
                f"\nNote: {custom_note.strip()}\n" if custom_note and custom_note.strip() else ""
            )
            message_text = (
                f"Dear {student_name},\n\n"
                f"This is a gentle fee reminder from {academy.name}.\n\n"
                f"• Student ID: {id_no}\n"
                f"• Course: {course_name}\n"
                f"• Due Period: {months_str}\n"
                f"• Total Due Amount: {amount_formatted}\n"
                f"{note_part}\n"
                f"Kindly clear the fee dues at the academy office or via online payment.\n\n"
                f"Thank you,\n{academy.name}"
            )

            if not contact_e164:
                skipped_no_contact += 1
                notified.append(
                    DueFeeNoticeResult(
                        student_id=student_id,
                        student_name=student_name,
                        contact=raw_contact,
                        contact_e164=None,
                        amount_paise=total_due_paise,
                        amount_formatted=amount_formatted,
                        unpaid_months=unpaid_months,
                        message_text=message_text,
                        whatsapp_url=None,
                        queued=False,
                    )
                )
                continue

            clean_phone = contact_e164.lstrip("+")
            whatsapp_url = f"https://wa.me/{clean_phone}?text={quote_plus(message_text)}"
            notif_id = None
            with self.db.transaction() as conn:
                notif_repo = NotificationRepository(conn)
                enqueued = notif_repo.enqueue(
                    student_id=student_id,
                    fee_id=None,
                    payment_id=None,
                    channel="WHATSAPP",
                    recipient=contact_e164,
                    template=NotificationTemplate.FEE_REMINDER.value,
                    payload={
                        "name": student_name,
                        "fee_title": f"Monthly Dues ({months_str})",
                        "amount": amount_formatted,
                        "due_date": "Immediate",
                        "academy_name": academy.name,
                    },
                    dedupe_key=f"bulk_fee_notice:{student_id}:{today_str}:{uuid4().hex[:8]}",
                )
                if enqueued:
                    notif_id = enqueued["id"]
                    queued_count += 1
                record_audit(
                    conn,
                    actor_id=actor.user_id,
                    action="notifications.bulk_due_reminder",
                    entity_type="student",
                    entity_id=student_id,
                    after={"recipient": contact_e164, "amount_paise": total_due_paise},
                )

            notified.append(
                DueFeeNoticeResult(
                    student_id=student_id,
                    student_name=student_name,
                    contact=raw_contact,
                    contact_e164=contact_e164,
                    amount_paise=total_due_paise,
                    amount_formatted=amount_formatted,
                    unpaid_months=unpaid_months,
                    message_text=message_text,
                    whatsapp_url=whatsapp_url,
                    queued=True,
                    notification_id=notif_id,
                )
            )

        try:
            notifications.process_due(batch_size=max(queued_count, 50))
        except Exception as e:
            logger.warning("Error processing notification queue in bulk run: %s", e)

        status_msg = (
            f"Queued WhatsApp fee notices for {queued_count} students "
            f"({skipped_no_contact} skipped without phone number)."
        )
        return BroadcastDueNoticeResult(
            total_unpaid=total_unpaid,
            queued_count=queued_count,
            skipped_no_contact=skipped_no_contact,
            message=status_msg,
            notified_students=notified,
        )

    def set_status(self, actor: CurrentUser, student_id: UUID, status: StudentStatus) -> Student:
        return self.update(actor, student_id, StudentUpdate(status=status))

    def upload_photo(
        self,
        actor: CurrentUser,
        student_id: UUID,
        *,
        data: bytes,
        filename: str | None,
        content_type: str | None,
    ) -> StudentPhotoResult:
        image = validate_image(data, filename, content_type)
        with self.db.transaction() as conn:
            if StudentRepository(conn).get_by_id(student_id) is None:
                raise StudentNotFoundError()

        # Photos are never overwritten: each upload gets a new path and the old file is kept.
        path = f"{student_id}/{uuid4().hex}.jpg"
        self.storage.upload(self.storage.photo_bucket, path, image.data, image.content_type)

        with self.db.transaction() as conn:
            repo = StudentRepository(conn)
            current = repo.lock(student_id)
            if current is None:
                raise StudentNotFoundError()
            repo.update_fields(student_id, {"photo_path": path})
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="student.photo_updated",
                entity_type="student",
                entity_id=student_id,
                before={"photo_path": current["photo_path"]},
                after={"photo_path": path},
            )

        generated, error = True, None
        try:
            self.id_cards.generate(actor, student_id)
        except AppError as exc:
            generated, error = False, exc.message
            logger.warning(
                "id card generation after photo upload failed",
                extra={"student_id": str(student_id), "code": exc.code},
            )
        return StudentPhotoResult(
            student=self.get(actor, student_id), id_card_generated=generated, id_card_error=error
        )

    def get_photo(self, user: CurrentUser, student_id: UUID) -> bytes:
        student = self.get(user, student_id)
        if student.photo_path is None:
            raise NotFoundError("No photo has been uploaded.", code="PHOTO_NOT_FOUND")
        return self.storage.download(self.storage.photo_bucket, student.photo_path)

    @staticmethod
    def _check_course(conn: DbConnection, course_id: UUID | None) -> None:
        if course_id is None:
            return
        course = CourseRepository(conn).get_by_id(course_id)
        if course is None:
            raise NotFoundError("Course was not found.", code="COURSE_NOT_FOUND")
        if not course["active"]:
            raise ValidationFailedError("This course is inactive.", code="COURSE_INACTIVE")
