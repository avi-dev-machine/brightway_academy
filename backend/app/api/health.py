"""Unversioned health checks. They never depend on optional integrations (WhatsApp, SMS)."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.dependencies import ContainerDep
from app.exceptions import AppError

router = APIRouter(tags=["health"])


def _unavailable(code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=503, content={"success": False, "error": {"code": code, "message": message}}
    )


@router.get("/health", response_model=None)
def health() -> dict[str, Any]:
    return {"success": True, "data": {"status": "ok"}}


@router.get("/health/db", response_model=None)
def health_db(container: ContainerDep) -> dict[str, Any] | JSONResponse:
    if not container.db.ping():
        return _unavailable("DATABASE_UNAVAILABLE", "Database is not reachable.")
    return {"success": True, "data": {"status": "ok"}}


@router.get("/health/storage", response_model=None)
def health_storage(container: ContainerDep) -> dict[str, Any] | JSONResponse:
    try:
        container.storage.ping()
    except (AppError, OSError):
        return _unavailable("STORAGE_UNAVAILABLE", "File storage is not reachable.")
    return {"success": True, "data": {"status": "ok", "backend": container.storage.backend_name}}
