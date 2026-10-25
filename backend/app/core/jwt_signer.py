"""Local ES256 JWT key management and token issuance.

Allows standalone and offline operation without depending on external Supabase Auth servers,
while producing standard ES256 signed JWTs completely compatible with the existing TokenVerifier.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.schemas.auth import TokenOut

_KEY_FILE = Path(__file__).resolve().parent.parent.parent / ".jwt_signing_key.pem"
_ISSUER = "https://brightway.academy/auth/v1"
_AUDIENCE = "authenticated"


def _get_or_create_key() -> ec.EllipticCurvePrivateKey:
    if _KEY_FILE.exists():
        try:
            return serialization.load_pem_private_key(_KEY_FILE.read_bytes(), password=None)  # type: ignore[return-value]
        except Exception:
            pass
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    _KEY_FILE.write_bytes(pem)
    return key


_SIGNING_KEY = _get_or_create_key()
_PUBLIC_KEY = _SIGNING_KEY.public_key()


def get_local_public_key() -> Any:
    return _PUBLIC_KEY


def get_local_issuer() -> str:
    return _ISSUER


def issue_token(
    user_id: UUID,
    *,
    email: str | None = None,
    expires_in: int = 86400 * 7,  # 7 days
) -> TokenOut:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "aud": _AUDIENCE,
        "iss": _ISSUER,
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "session_id": str(uuid4()),
        "email": email,
    }
    access_token = jwt.encode(payload, _SIGNING_KEY, algorithm="ES256")
    refresh_token = f"ref_{uuid4().hex}_{user_id.hex}"
    return TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user_id=user_id,
    )
