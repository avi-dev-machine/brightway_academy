"""Parser for the academy's legacy fee sheets ("brightway student record - cert/non cert").

Sheet layout (both files):

    NAME, STUDENT ID, CONTACT NO., COURSE, FEES, <one column per month from January 2023>

Every month cell holds whatever was written when that month's fee was collected: usually
the date it was received ("10 Apr", "5JULLY", "11 February 2026", "02/04/2026"), sometimes
"paid", "closed", a day number, or free text. The month columns are mapped by POSITION
(column 6 = January 2023, column 7 = February 2023, ...) because the header labels are
inconsistent ("JULLY", "June", a second "SEP" after "Oct").

This module is pure (no database access) so it can be unit-tested and used to produce a
preview report before anything is written.
"""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from app.utils.validators import normalize_indian_phone, normalize_whitespace

FIRST_PERIOD = date(2023, 1, 1)
EXPECTED_HEADER = ("name", "student id", "contact no.", "course", "fees")
MONTH_COLUMNS_START = len(EXPECTED_HEADER)

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}  # fmt: skip
MONTH_NAMES = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)  # fmt: skip

_TEXT_DATE = re.compile(r"(\d{1,2})\s*[ ,.\-]?\s*([a-z]{3,10})\.?(?:\s*[ ,'\-]?\s*(\d{4}|\d{2})\b)?")
_NUMERIC_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
_DAY_ONLY = re.compile(r"^\d{1,2}$")
_PAID = re.compile(r"^paid\W*$")
_PENDING = re.compile(r"pending\s*(?:rs\.?\s*)?(\d+)")
_ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8,
          "ix": 9, "x": 10, "xi": 11, "xii": 12}  # fmt: skip
_ID_PATTERN = re.compile(r"^(RG|BW)\d{6}[A-Z]?$")


class Program(StrEnum):
    CERTIFICATE = "CERTIFICATE"
    NON_CERTIFICATE = "NON_CERTIFICATE"


class EntryStatus(StrEnum):
    PAID = "PAID"  # paid, date known
    PAID_UNDATED = "PAID_UNDATED"  # sheet only says "paid"
    PARTIAL = "PARTIAL"  # paid with an amount still pending
    CLOSED = "CLOSED"  # course closed from this month
    ABSENT = "ABSENT"  # student absent, no fee taken
    UNCLEAR = "UNCLEAR"  # something written that is not a payment record


@dataclass
class FeeEntry:
    period: date  # first day of the month the fee belongs to
    status: EntryStatus
    raw: str  # exactly what the cell said
    paid_on: date | None = None
    note: str | None = None
    pending_paise: int | None = None


@dataclass
class CourseRef:
    code: str
    name: str


@dataclass
class SheetStudent:
    program: Program
    source_file: str
    row_number: int  # line number in the CSV file (header = 1)
    name: str
    raw_name: str
    id_no: str | None
    sheet_id_no: str | None  # the ID exactly as written, kept even if it had to be dropped
    contact: str | None
    contact_e164: str | None
    course: CourseRef | None
    course_raw: str | None
    monthly_fee_paise: int | None
    fee_note: str | None
    entries: list[FeeEntry] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.name} ({self.id_no or 'no ID'}, {self.source_file} row {self.row_number})"

    @property
    def paid_entries(self) -> list[FeeEntry]:
        return [e for e in self.entries if e.status in _PAID_STATUSES]

    @property
    def last_paid_period(self) -> date | None:
        periods = [e.period for e in self.paid_entries]
        return max(periods) if periods else None


_PAID_STATUSES = (EntryStatus.PAID, EntryStatus.PAID_UNDATED, EntryStatus.PARTIAL)


@dataclass
class SkippedRow:
    source_file: str
    row_number: int
    reason: str


@dataclass
class ParsedSheet:
    students: list[SheetStudent]
    skipped: list[SkippedRow]
    header_warnings: list[str]
    last_period: date


class SheetFormatError(ValueError):
    pass


# ---------------------------------------------------------------------- small helpers
def add_months(start: date, months: int) -> date:
    index = start.year * 12 + (start.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def period_label(period: date) -> str:
    return f"{MONTH_NAMES[period.month - 1]} {period.year}"


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _month_from_word(word: str) -> int | None:
    word = word.lower()
    if word.startswith("sept"):
        return 9
    return _MONTHS.get(word[:3])


def _score(candidate: date, period: date) -> int:
    """How plausible a payment date is for a fee month: payments are normally made in
    that month or later (late fees are common); paying well in advance is rare."""
    offset = (candidate - period).days
    return offset if offset >= 0 else -offset * 3


def _best(candidates: list[date], period: date) -> date | None:
    valid = [c for c in candidates if c is not None]
    return min(valid, key=lambda c: _score(c, period)) if valid else None


def _expand_year(text: str | None) -> int | None:
    if not text:
        return None
    year = int(text)
    return year + 2000 if year < 100 else year


def _find_dates(text: str, period: date) -> list[date]:
    """Every date mentioned in a cell, resolved against the fee month it was written in."""
    found: list[tuple[int, date]] = []
    for match in _NUMERIC_DATE.finditer(text):
        a, b, year = int(match.group(1)), int(match.group(2)), _expand_year(match.group(3))
        if year is None:
            continue
        options = [_safe_date(year, b, a), _safe_date(year, a, b)]  # DD/MM or MM/DD
        best = _best([o for o in options if o], period)
        if best:
            found.append((match.start(), best))
    for match in _TEXT_DATE.finditer(text):
        month = _month_from_word(match.group(2))
        if month is None:
            continue
        day = int(match.group(1))
        year = _expand_year(match.group(3))
        if year is not None:
            candidate = _safe_date(year, month, day)
            if candidate:
                found.append((match.start(), candidate))
            continue
        options = [_safe_date(period.year + d, month, day) for d in (-1, 0, 1)]
        best = _best([o for o in options if o], period)
        if best:
            found.append((match.start(), best))
    return [d for _, d in sorted(found, key=lambda item: item[0])]


# ---------------------------------------------------------------------- cell parsing
def parse_fee_cell(raw: str, period: date) -> FeeEntry | None:
    """Interpret one month cell. Returns None for an empty cell."""
    text = normalize_whitespace(raw)
    if not text:
        return None
    lower = text.lower()
    if _PAID.match(lower):
        return FeeEntry(period, EntryStatus.PAID_UNDATED, text, note="Marked 'paid' without a date")
    if lower.startswith("closed"):
        return FeeEntry(period, EntryStatus.CLOSED, text, note="Course closed")
    if lower.startswith("absent"):
        return FeeEntry(period, EntryStatus.ABSENT, text, note="Student absent, no fee")
    if _DAY_ONLY.match(lower):
        paid_on = _safe_date(period.year, period.month, int(lower))
        if paid_on is None:
            return FeeEntry(period, EntryStatus.UNCLEAR, text, note="Day number is not a valid date")
        return FeeEntry(period, EntryStatus.PAID, text, paid_on, note="Only the day was written")

    dates = _find_dates(lower, period)
    pending = _PENDING.search(lower)
    notes: list[str] = []
    if len(dates) > 1:
        notes.append("Several dates written; first one used")
    if "×" in lower or " x " in f" {lower} ":
        notes.append("Marked as more than one payment")
    if "(" in lower:
        notes.append(f"Remark: {text[text.index('(') :].strip('() ')}")
    if pending:
        notes.append(f"Rs {pending.group(1)} pending")
    if not dates:
        return FeeEntry(period, EntryStatus.UNCLEAR, text, note="Not a recognisable date")
    paid_on = dates[0]
    offset = (paid_on - period).days
    if offset < -100 or offset > 550:
        notes.append("Payment date is far from the fee month; please verify")
    return FeeEntry(
        period,
        EntryStatus.PARTIAL if pending else EntryStatus.PAID,
        text,
        paid_on,
        note="; ".join(notes) or None,
        pending_paise=int(pending.group(1)) * 100 if pending else None,
    )


# ---------------------------------------------------------------------- column parsing
def normalize_course(raw: str | None) -> tuple[CourseRef | None, str | None]:
    """Map a free-text course cell to a course code/name. Returns (course, issue)."""
    text = normalize_whitespace(raw)
    if not text:
        return None, None
    upper = re.sub(r"[\s.\-]", "", text.upper())
    note = None
    if ">" in upper:  # "CIT> DCA": moved from one course to another
        before, upper = upper.split(">", 1)[0], upper.split(">")[-1]
        note = f"Course changed from {before} to {upper}"
    school = re.fullmatch(r"(?:CLASS|CLAS)?([IVX]+|\d{1,2})", upper)
    if school:
        token = school.group(1)
        grade = int(token) if token.isdigit() else _ROMAN.get(token.lower())
        if grade and 1 <= grade <= 12:
            return CourseRef(code=f"CLASS-{grade}", name=f"Class {grade}"), note
    aliases = {"PROGRAMING": "PROGRAMMING"}
    code = aliases.get(upper, upper)
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,31}", code):
        return None, f"Course '{text}' could not be understood"
    names = {"PYTHON": "Python", "PROGRAMMING": "Programming", "EXCEL": "Excel"}
    return CourseRef(code=code, name=names.get(code, code)), note


def _parse_fee(raw: str | None) -> tuple[int | None, str | None, str | None]:
    """FEES column -> (monthly fee in paise, note, issue)."""
    text = normalize_whitespace(raw)
    if not text:
        return None, None, None
    digits = text.replace(",", "")
    if digits.isdigit():
        return int(digits) * 100, None, None
    if "paid" in text.lower():
        return None, text.upper(), None
    return None, None, f"FEES column contained '{text}' instead of an amount"


def default_passcode(name: str, id_no: str) -> str:
    """Universal student passcode rule: first 3 letters of the name (capitals) followed by
    the last 4 digits of the student ID. AGNIRUDRA BASU / RG240017 -> AGN0017."""
    letters = "".join(ch for ch in name.upper() if "A" <= ch <= "Z")
    digits = "".join(ch for ch in id_no if ch.isdigit())
    return (letters[:3].ljust(3, "X")) + digits[-4:].rjust(4, "0")


# ---------------------------------------------------------------------- sheet parsing
def parse_sheet(text: str, program: Program, source_file: str) -> ParsedSheet:
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    if not rows:
        raise SheetFormatError(f"{source_file}: file is empty")
    header = [(h or "").strip().lower() for h in rows[0]]
    if tuple(header[:MONTH_COLUMNS_START]) != EXPECTED_HEADER:
        raise SheetFormatError(
            f"{source_file}: first columns must be {', '.join(EXPECTED_HEADER)}; got {header[:5]}"
        )
    month_count = len(header) - MONTH_COLUMNS_START
    header_warnings: list[str] = []
    for index, label in enumerate(header[MONTH_COLUMNS_START:]):
        expected = add_months(FIRST_PERIOD, index)
        month = _month_from_word(re.sub(r"[^a-z]", "", label)) if label else None
        if month is not None and month != expected.month:
            header_warnings.append(
                f"Column {index + MONTH_COLUMNS_START + 1} is labelled '{label.strip()}' but its "
                f"position is {period_label(expected)}; position was used"
            )

    students: list[SheetStudent] = []
    skipped: list[SkippedRow] = []
    for line_no, row in enumerate(rows[1:], start=2):
        cells = (row + [""] * len(header))[: len(header)]
        if not any(c.strip() for c in cells):
            skipped.append(SkippedRow(source_file, line_no, "Empty row"))
            continue
        students.append(_parse_row(cells, line_no, program, source_file, month_count))
    return ParsedSheet(
        students, skipped, header_warnings, add_months(FIRST_PERIOD, month_count - 1)
    )


def _parse_row(
    cells: list[str], line_no: int, program: Program, source_file: str, month_count: int
) -> SheetStudent:
    raw_name, raw_id, raw_contact, raw_course, raw_fee = cells[:MONTH_COLUMNS_START]
    issues: list[str] = []
    name = (normalize_whitespace(raw_name.replace(";", " ")) or "").upper()
    if not name:
        name = f"NAME MISSING ({source_file} row {line_no})"
        issues.append("Name is missing in the sheet")

    sheet_id = (normalize_whitespace(raw_id) or "").upper() or None
    if sheet_id is None:
        issues.append("No student ID in the sheet")
    elif not _ID_PATTERN.match(sheet_id):
        issues.append(f"Student ID '{sheet_id}' does not follow the usual pattern")

    contact = normalize_whitespace(raw_contact)
    e164 = normalize_indian_phone(contact)
    if contact and e164 is None:
        issues.append(f"Phone number '{contact}' is not a valid 10-digit mobile number")

    # Some rows have the course written one column to the right (in FEES).
    fee_cell = raw_fee
    course_cell = raw_course
    if not normalize_whitespace(raw_course) and raw_fee.strip() and not any(
        ch.isdigit() for ch in raw_fee
    ) and "paid" not in raw_fee.lower():
        course_cell, fee_cell = raw_fee, ""
        issues.append(f"Course '{raw_fee.strip()}' was written in the FEES column")
    course, course_issue = normalize_course(course_cell)
    if course_issue:
        issues.append(course_issue)
    fee_paise, fee_note, fee_issue = _parse_fee(fee_cell)
    if fee_issue:
        issues.append(fee_issue)

    entries: list[FeeEntry] = []
    for index in range(month_count):
        period = add_months(FIRST_PERIOD, index)
        entry = parse_fee_cell(cells[MONTH_COLUMNS_START + index], period)
        if entry is None:
            continue
        if entry.status == EntryStatus.UNCLEAR:
            issues.append(f"{period_label(period)}: unclear entry '{entry.raw}'")
        elif entry.note and "verify" in entry.note:
            issues.append(f"{period_label(period)}: '{entry.raw}' is far from the fee month")
        entries.append(entry)
    if not entries:
        issues.append("No fee records in the sheet")

    return SheetStudent(
        program=program,
        source_file=source_file,
        row_number=line_no,
        name=name,
        raw_name=raw_name,
        id_no=sheet_id,
        sheet_id_no=sheet_id,
        contact=contact,
        contact_e164=e164,
        course=course,
        course_raw=normalize_whitespace(raw_course),
        monthly_fee_paise=fee_paise,
        fee_note=fee_note,
        entries=entries,
        issues=issues,
    )


# ---------------------------------------------------------------------- cross-row checks
def reconcile(students: list[SheetStudent]) -> None:
    """Checks across all rows of both sheets (mutates the students in place):

    * a student ID used by more than one row stays only on the first row; later rows are
      imported without an ID and both rows are flagged;
    * same name appearing twice in the same sheet is flagged as a possible duplicate;
    * same name appearing in both sheets is flagged as "also enrolled as ...".
    """
    by_id: dict[str, list[SheetStudent]] = defaultdict(list)
    for student in students:
        if student.id_no:
            by_id[student.id_no.lower()].append(student)
    for group in by_id.values():
        if len(group) < 2:
            continue
        keeper, *others = group
        for other in others:
            other.id_no = None
            other.issues.append(
                f"Student ID {other.sheet_id_no} is also written for {keeper.label}; "
                "kept on that row only, this row has no ID until one is assigned"
            )
        keeper.issues.append(
            "Same student ID also written for "
            + ", ".join(f"{o.name} ({o.source_file} row {o.row_number})" for o in others)
        )

    by_name: dict[str, list[SheetStudent]] = defaultdict(list)
    for student in students:
        if not student.name.startswith("NAME MISSING"):
            by_name[re.sub(r"[^A-Z]", "", student.name)].append(student)
    for group in by_name.values():
        if len(group) < 2:
            continue
        for student in group:
            for other in group:
                if other is student:
                    continue
                if other.program == student.program:
                    student.issues.append(f"Possible duplicate of {other.label}")
                else:
                    student.issues.append(
                        f"Also enrolled in {other.program.value.replace('_', '-').lower()}"
                        f" as {other.label}"
                    )


def derive_status(student: SheetStudent, today: date, active_months: int = 3) -> str:
    """'active' when a fee month within the last `active_months` months (or later) is paid
    and the course was not closed afterwards; otherwise 'inactive'.
    With today = 24 Oct 2026 and 3 months, a student whose latest paid month is July 2026
    or later is active."""
    last_paid = student.last_paid_period
    if last_paid is None:
        return "inactive"
    closed = [e.period for e in student.entries if e.status == EntryStatus.CLOSED]
    if closed and max(closed) >= last_paid:
        return "inactive"
    cutoff = add_months(date(today.year, today.month, 1), -active_months)
    return "active" if last_paid >= cutoff else "inactive"
