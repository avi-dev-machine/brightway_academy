from fastapi import APIRouter

from app.api.v1 import (
    admin,
    attendance,
    auth,
    batches,
    courses,
    fees,
    id_cards,
    imports,
    notifications,
    payments,
    receipts,
    reports,
    students,
    teachers,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(batches.router, prefix="/batches", tags=["batches"])
api_router.include_router(teachers.router, prefix="/teachers", tags=["teachers"])
api_router.include_router(fees.router, prefix="/fees", tags=["fees"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(receipts.router, prefix="/receipts", tags=["receipts"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(id_cards.router, prefix="/id-cards", tags=["id-cards"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
