from datetime import date
from uuid import UUID

from pydantic import BaseModel


class CourseCount(BaseModel):
    course_id: UUID | None
    course_name: str
    count: int


class DashboardStats(BaseModel):
    students_active: int
    students_inactive: int
    students_total: int
    students_by_course: list[CourseCount]
    fees_outstanding_paise: int
    fees_overdue_paise: int
    fees_overdue_count: int
    collected_today_paise: int
    payments_today: int
    collected_this_month_paise: int
    attendance_today_marked: int
    attendance_today_attended: int


class CollectionRow(BaseModel):
    day: date
    provider: str
    method: str
    count: int
    amount_paise: int


class CollectionReport(BaseModel):
    date_from: date
    date_to: date
    rows: list[CollectionRow]
    total_count: int
    total_paise: int


class OutstandingRow(BaseModel):
    student_id: UUID
    id_no: str
    name: str
    contact: str | None
    course_name: str | None
    outstanding_paise: int
    overdue_paise: int
    oldest_due_date: date
