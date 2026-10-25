"""FastAPI application factory. Run with: uvicorn app.main:app"""

import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api import health
from app.api.v1.router import api_router
from app.config import Settings, get_settings
from app.core.constants import API_V1_PREFIX
from app.core.errors import register_exception_handlers
from app.dependencies import Container, build_container
from app.logging import configure_logging, request_id_var

logger = logging.getLogger("app.request")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestContextMiddleware:
    """Assigns a request ID, adds security headers and logs one structured line per request."""

    def __init__(self, app: ASGIApp, *, hsts: bool = False) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _REQUEST_ID.match(incoming) else uuid4().hex
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        token = request_id_var.set(request_id)
        started = perf_counter()
        status_code = 500

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "no-referrer")
                headers.setdefault("X-XSS-Protection", "1; mode=block")
                headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
                if self.hsts:
                    headers.setdefault(
                        "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
                    )
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            client = scope.get("client")
            logger.info(
                "request completed",
                extra={
                    "operation": "http_request",
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                    "user_id": state.get("user_id"),
                    "client_ip": client[0] if client else None,
                },
            )
            request_id_var.reset(token)


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = container is None
        active = container if container is not None else build_container(settings)
        if owned:
            active.open()
        app.state.container = active
        logger.info(
            "application started",
            extra={
                "operation": "startup",
                "app_env": settings.app_env,
                "payment_provider": active.payment_provider.name,
                "storage_backend": active.storage.backend_name,
                "notification_channels": sorted(active.notification_providers),
            },
        )
        try:
            yield
        finally:
            if owned:
                active.close()

    app = FastAPI(
        title="Brightway Computer Academy API",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    if container is not None:
        app.state.container = container

    register_exception_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Content-Disposition"],
    )
    app.add_middleware(RequestContextMiddleware, hsts=settings.is_production)

    app.include_router(health.router)
    app.include_router(api_router, prefix=API_V1_PREFIX)
    return app


app = create_app()
