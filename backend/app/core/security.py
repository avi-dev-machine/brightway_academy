"""Verification of Supabase Auth access tokens signed with asymmetric keys (JWKS)."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from app.exceptions import ExternalServiceError, UnauthorizedError

logger = logging.getLogger(__name__)

# Only asymmetric algorithms are accepted, which rules out HS256 key-confusion attacks.
ALLOWED_ALGORITHMS = ["ES256", "RS256", "EdDSA"]

KeyResolver = Callable[[str], Any]


@dataclass(frozen=True)
class TokenClaims:
    user_id: UUID
    email: str | None
    session_id: str | None


class TokenVerifier:
    def __init__(
        self,
        issuer: str | list[str],
        key_resolver: KeyResolver,
        audience: str = "authenticated",
        leeway_seconds: int = 30,
    ) -> None:
        self._issuer = issuer
        self._key_resolver = key_resolver
        self._audience = audience
        self._leeway = leeway_seconds

    @classmethod
    def for_supabase(cls, supabase_url: str) -> "TokenVerifier":
        from app.core.jwt_signer import get_local_issuer, get_local_public_key

        base = supabase_url.rstrip("/") if supabase_url else "https://supabase.invalid"
        jwks = PyJWKClient(
            f"{base}/auth/v1/.well-known/jwks.json", cache_keys=True, lifespan=600, timeout=5
        )

        def resolve(token: str) -> Any:
            try:
                unverified_header = jwt.get_unverified_header(token)
                if unverified_header.get("kid"):
                    return jwks.get_signing_key_from_jwt(token).key
            except Exception:
                pass
            return get_local_public_key()

        issuers = [f"{base}/auth/v1", get_local_issuer()]
        return cls(issuer=issuers, key_resolver=resolve)

    def verify(self, token: str) -> TokenClaims:
        try:
            key = self._key_resolver(token)
            claims = jwt.decode(
                token,
                key=key,
                algorithms=ALLOWED_ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway,
                options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError(
                "Your session has expired. Please sign in again.", code="TOKEN_EXPIRED"
            ) from exc
        except PyJWKClientConnectionError as exc:
            logger.error(
                "could not fetch auth signing keys", extra={"error_type": type(exc).__name__}
            )
            raise ExternalServiceError("Authentication service is unavailable.") from exc
        except (PyJWKClientError, jwt.InvalidTokenError) as exc:
            raise UnauthorizedError("Invalid authentication token.", code="INVALID_TOKEN") from exc

        if claims.get("role") != "authenticated" or claims.get("is_anonymous") is True:
            raise UnauthorizedError("Invalid authentication token.", code="INVALID_TOKEN")
        try:
            user_id = UUID(str(claims["sub"]))
        except ValueError as exc:
            raise UnauthorizedError("Invalid authentication token.", code="INVALID_TOKEN") from exc
        return TokenClaims(
            user_id=user_id, email=claims.get("email"), session_id=claims.get("session_id")
        )
