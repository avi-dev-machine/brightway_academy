"""Thin client for the Supabase Auth (GoTrue) REST API."""

import logging
from typing import Any
from uuid import UUID

import httpx

from app.exceptions import (
    ConflictError,
    ExternalServiceError,
    RateLimitedError,
    ServiceNotConfiguredError,
    UnauthorizedError,
)

logger = logging.getLogger(__name__)


class SupabaseAuthClient:
    def __init__(
        self,
        supabase_url: str,
        publishable_key: str,
        service_role_key: str = "",
        *,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base = f"{supabase_url.rstrip('/')}/auth/v1"
        self._publishable_key = publishable_key
        self._service_key = service_role_key
        self._http = httpx.Client(timeout=timeout, transport=transport)

    @property
    def admin_configured(self) -> bool:
        return bool(self._service_key)

    def close(self) -> None:
        self._http.close()

    def sign_in_with_password(self, email: str, password: str) -> dict[str, Any]:
        return self._token_request("password", {"email": email, "password": password})

    def refresh_session(self, refresh_token: str) -> dict[str, Any]:
        return self._token_request("refresh_token", {"refresh_token": refresh_token})

    def invite_user(self, email: str) -> UUID:
        """Create a user and send them an invite email. Requires the service-role key."""
        if not self._service_key:
            raise ServiceNotConfiguredError(
                "Inviting users requires SUPABASE_SERVICE_ROLE_KEY. "
                "Create the user in the Supabase dashboard and link it instead."
            )
        response = self._send(
            "POST",
            "/invite",
            json={"email": email},
            headers={"apikey": self._service_key, "Authorization": f"Bearer {self._service_key}"},
        )
        if response.status_code in (200, 201):
            return UUID(response.json()["id"])
        if response.status_code == 422:
            raise ConflictError(
                "A user with this email already exists. Link the existing account instead.",
                code="AUTH_USER_EXISTS",
            )
        raise self._unexpected(response)

    def _token_request(self, grant_type: str, body: dict[str, str]) -> dict[str, Any]:
        if not self._publishable_key:
            raise ServiceNotConfiguredError("Supabase Auth is not configured.")
        response = self._send(
            "POST",
            "/token",
            params={"grant_type": grant_type},
            json=body,
            headers={"apikey": self._publishable_key},
        )
        if response.status_code == 200:
            data: dict[str, Any] = response.json()
            return data
        if response.status_code == 429:
            raise RateLimitedError()
        if response.status_code in (400, 401, 403, 422):
            error_code = _error_code(response)
            if error_code == "email_not_confirmed":
                raise UnauthorizedError(
                    "Email address is not confirmed.", code="EMAIL_NOT_CONFIRMED"
                )
            if grant_type == "password":
                raise UnauthorizedError("Invalid email or password.", code="INVALID_CREDENTIALS")
            raise UnauthorizedError(
                "Session is no longer valid. Please sign in again.", code="INVALID_REFRESH_TOKEN"
            )
        raise self._unexpected(response)

    def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            return self._http.request(method, f"{self._base}{path}", **kwargs)
        except httpx.HTTPError as exc:
            logger.error("supabase auth request failed", extra={"error_type": type(exc).__name__})
            raise ExternalServiceError("Authentication service is unavailable.") from exc

    @staticmethod
    def _unexpected(response: httpx.Response) -> ExternalServiceError:
        logger.error(
            "unexpected supabase auth response", extra={"status_code": response.status_code}
        )
        return ExternalServiceError("Authentication service returned an unexpected error.")


def _error_code(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    if isinstance(body, dict):
        code = body.get("error_code") or body.get("code")
        return str(code) if code is not None else None
    return None
