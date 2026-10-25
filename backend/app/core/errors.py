"""Exception handlers that turn every error into the standard JSON error envelope."""

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import AppError

logger = logging.getLogger(__name__)


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", None),
    }
    if details is not None:
        error["details"] = jsonable_encoder(details)
    return JSONResponse(
        status_code=status_code, content={"success": False, "error": error}, headers=headers
    )


def _status_name(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).name
    except ValueError:
        return "HTTP_ERROR"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("application error", extra={"code": exc.code, "detail": exc.message})
        headers = dict(exc.headers or {})
        if exc.status_code == 401:
            headers.setdefault("WWW-Authenticate", "Bearer")
        return error_response(
            request, exc.status_code, exc.code, exc.message, exc.details, headers or None
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Submitted values are deliberately not echoed back (they may contain passwords).
        details = [
            {
                "field": ".".join(str(part) for part in err.get("loc", ())),
                "message": err.get("msg", ""),
                "type": err.get("type", ""),
            }
            for err in exc.errors()
        ]
        return error_response(
            request, 422, "VALIDATION_ERROR", "The request contains invalid data.", details
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else HTTPStatus(exc.status_code).phrase
        return error_response(
            request,
            exc.status_code,
            _status_name(exc.status_code),
            message,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled error", exc_info=exc)
        return error_response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.")
