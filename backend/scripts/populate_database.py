"""Master migration script for Brightway Computer Academy.

Executes:
  Task 1: Parses, cleans, and organizes all student and fee records from both CSVs
          into a clean database with courses, students, and structured monthly fees.
  Task 2: Sets student IDs and generates unique universal passcodes
          (first 3 letters of name in caps + last 4 digits of student ID).
  Task 3: Sets Admin ID 'BWADMIN' with secure passcode 'Brightway@Admin2026!'.
"""

import json
from datetime import date
from pathlib import Path
from uuid import uuid4

import psycopg
from app.core.passwords import hash_password
from app.services.legacy_sheet_parser import (
    EntryStatus,
    Program,
    default_passcode,
    derive_status,
    parse_sheet,
    period_label,
    reconcile,
)

ROOT = Path(__file__).resolve().parent.parent.parent
CERT_CSV = ROOT / "brightway student record - cert.csv"
NON_CERT_CSV = ROOT / "brightway student record - non cert.csv"
DB_URL_FILE = ROOT / "backend" / ".db_url"

TODAY = date(2026, 10, 24)
ADMIN_ID = "BWADMIN"
ADMIN_PASSCODE = "Brightway@Admin2026!"
ADMIN_EMAIL = "admin@brightway.academy"

COURSE_DEFINITIONS = [
    ("ADOAP", "Advanced Diploma in Office Automation & Publishing", 12, 90000),
    ("DCA", "Diploma in Computer Applications", 6, 80000),
    ("DCAE", "Diploma in Computer Applications & Entry", 6, 90000),
    ("ADCA", "Advanced Diploma in Computer Applications", 12, 100000),
    ("ADCP", "Advanced Diploma in Computer Programming", 12, 100000),
    ("ADV", "Advanced Excel & Tally", 6, 80000),
    ("BASIC", "Certificate in Basic Computing", 3, 80000),
    ("CIT", "Certificate in Information Technology", 6, 80000),
    ("DCAD", "Diploma in Computer Aided Design", 6, 90000),
    ("DCMS", "Diploma in Computer Management & Secretarial", 6, 90000),
    ("DDTP", "Diploma in Desktop Publishing", 6, 90000),
    ("EXCEL", "Certificate in Advanced Excel", 3, 80000),
    ("MDDIP", "Master Diploma in Digital Information Processing", 12, 100000),
    ("MDDTP", "Master Diploma in Desktop Publishing", 12, 90000),
    ("PROGRAMMING", "Computer Programming & Logic", 6, 100000),
    ("PYTHON", "Python Programming for Beginners & Advanced", 6, 400000),
    ("RCIT", "Regional Certificate in Information Technology", 6, 80000),
    ("CLASS-2", "Foundation Computing (Class 2)", 12, 50000),
    ("CLASS-4", "School Computer Science (Class 4)", 12, 50000),
    ("CLASS-5", "School Computer Science (Class 5)", 12, 50000),
    ("CLASS-6", "School Computer Science (Class 6)", 12, 50000),
    ("CLASS-7", "School Computer Science (Class 7)", 12, 60000),
    ("CLASS-8", "School Computer Science (Class 8)", 12, 50000),
    ("CLASS-9", "School Computer Science (Class 9)", 12, 60000),
    ("CLASS-10", "Board Computer Applications (Class 10)", 12, 60000),
    ("CLASS-11", "Senior Secondary Computing (Class 11)", 12, 80000),
    ("CLASS-12", "Senior Secondary Computing (Class 12)", 12, 80000),
]


def main() -> None:
    db_url = DB_URL_FILE.read_text(encoding="utf-8").strip()
    print(f"Connecting to database at {db_url}...")

    with psycopg.connect(db_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            # 1. Clean existing records for fresh idempotent load
            print("Preparing database tables...")
            cur.execute("truncate table student_monthly_fees cascade;")
            cur.execute("truncate table payments cascade;")
            cur.execute("truncate table fees cascade;")
            cur.execute("delete from user_profiles;")
            cur.execute("delete from students;")

            # 2. Seed Admin user (Task 3)
            print(f"Seeding Admin account: ID='{ADMIN_ID}', Passcode='{ADMIN_PASSCODE}'...")
            admin_user_id = uuid4()
            cur.execute(
                """
                insert into user_profiles (user_id, identifier, email, role, password_hash, active)
                values (%s, %s, %s, 'ADMIN', %s, true)
                """,
                (admin_user_id, ADMIN_ID, ADMIN_EMAIL, hash_password(ADMIN_PASSCODE)),
            )

            # 3. Seed Courses
            print("Ensuring courses catalog...")
            course_id_map: dict[str, str] = {}
            for code, name, duration, fee_paise in COURSE_DEFINITIONS:
                cur.execute(
                    """
                    insert into courses (code, name, duration_months, default_fee_paise, active)
                    values (%s, %s, %s, %s, true)
                    on conflict (code) do update set
                        name = excluded.name,
                        default_fee_paise = excluded.default_fee_paise
                    returning id
                    """,
                    (code, name, duration, fee_paise),
                )
                cid = cur.fetchone()[0]
                course_id_map[code] = cid

            # Also index any existing courses by name/code
            cur.execute("select id, code from courses")
            for cid, code in cur.fetchall():
                course_id_map[code] = cid

            # 4. Parse Legacy Sheets (Task 1)
            print(f"Reading certificate students from '{CERT_CSV.name}'...")
            cert_sheet = parse_sheet(
                CERT_CSV.read_text(encoding="utf-8"),
                Program.CERTIFICATE,
                "cert",
            )
            print(f"Reading non-certificate students from '{NON_CERT_CSV.name}'...")
            non_cert_sheet = parse_sheet(
                NON_CERT_CSV.read_text(encoding="utf-8"),
                Program.NON_CERTIFICATE,
                "non-cert",
            )

            all_students = cert_sheet.students + non_cert_sheet.students
            print(f"Total student entries parsed: {len(all_students)}")
            reconcile(all_students)

            # 5. Insert Students & User Credentials (Task 2)
            print("Inserting students and generating universal passcodes...")
            inserted_students = 0
            inserted_logins = 0
            inserted_fees = 0

            for s in all_students:
                student_id = uuid4()
                course_id = course_id_map.get(s.course.code) if s.course else None
                status = derive_status(s, TODAY)
                passcode = default_passcode(s.name, s.id_no) if s.id_no else None

                cur.execute(
                    """
                    insert into students (
                        id, id_no, name, guardian_name, address, contact, contact_e164,
                        course_id, legacy_course, admission_date, status, program,
                        monthly_fee_paise, fee_notes, initial_passcode, issues
                    ) values (
                        %s, %s, %s, null, null, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    """,
                    (
                        student_id,
                        s.id_no,
                        s.name,
                        s.contact,
                        s.contact_e164,
                        course_id,
                        s.course_raw,
                        TODAY,
                        status,
                        s.program.value,
                        s.monthly_fee_paise,
                        s.fee_note,
                        passcode,
                        json.dumps(s.issues),
                    ),
                )
                inserted_students += 1

                # If student has an ID, create their login profile
                if s.id_no and passcode:
                    user_id = uuid4()
                    cur.execute(
                        """
                        insert into user_profiles (
                            user_id, identifier, role, student_id, password_hash, active
                        ) values (%s, %s, 'STUDENT', %s, %s, true)
                        """,
                        (user_id, s.id_no, student_id, hash_password(passcode)),
                    )
                    inserted_logins += 1

                # 6. Insert detailed monthly fees
                for entry in s.entries:
                    label = period_label(entry.period)
                    cur.execute(
                        """
                        insert into student_monthly_fees (
                            student_id, period, period_label, amount_paise, status,
                            paid_on, raw_entry, note, pending_paise
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict (student_id, period) do nothing
                        """,
                        (
                            student_id,
                            entry.period,
                            label,
                            s.monthly_fee_paise,
                            entry.status.value,
                            entry.paid_on,
                            entry.raw,
                            entry.note,
                            entry.pending_paise,
                        ),
                    )
                    inserted_fees += 1

                    # Also create regular fees & payment records for paid entries
                    if entry.status in (EntryStatus.PAID, EntryStatus.PAID_UNDATED, EntryStatus.PARTIAL):
                        fee_id = uuid4()
                        amount = s.monthly_fee_paise or 80000
                        cur.execute(
                            """
                            insert into fees (
                                id, student_id, fee_type, title, amount_paise, paid_paise,
                                due_date, status, created_at
                            ) values (%s, %s, 'MONTHLY', %s, %s, %s, %s, 'PAID', now())
                            """,
                            (
                                fee_id,
                                student_id,
                                f"Fee for {label}",
                                amount,
                                amount,
                                entry.period,
                            ),
                        )
                        payment_id = uuid4()
                        cur.execute(
                            """
                            insert into payments (
                                id, fee_id, student_id, amount_paise, provider, method,
                                status, paid_at, reference, notes, created_at
                            ) values (%s, %s, %s, %s, 'OFFLINE', 'CASH', 'SUCCESS', %s, %s, %s, now())
                            """,
                            (
                                payment_id,
                                fee_id,
                                student_id,
                                amount,
                                entry.paid_on or entry.period,
                                entry.raw,
                                entry.note,
                            ),
                        )

        conn.commit()

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Total students migrated:      {inserted_students}")
    print(f"  - Certificate students:     {len(cert_sheet.students)}")
    print(f"  - Non-certificate students: {len(non_cert_sheet.students)}")
    print(f"Total student logins created: {inserted_logins}")
    print(f"Total fee records created:    {inserted_fees}")
    print("\nADMIN CREDENTIALS (Task 3):")
    print(f"  Admin ID:       {ADMIN_ID}")
    print(f"  Admin Passcode: {ADMIN_PASSCODE}")
    print("\nSTUDENT CREDENTIAL LOGIC (Task 2):")
    print("  Student ID:     As in database (e.g. RG240017, BW240004)")
    print("  Passcode:       First 3 letters of name + last 4 digits of ID (e.g. AGN0017)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
