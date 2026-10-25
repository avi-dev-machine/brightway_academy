"""Password and passcode hashing using PBKDF2-HMAC-SHA256."""

import hashlib
import hmac
import os


def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with a 16-byte cryptographically secure salt."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"pbkdf2_sha256$100000${salt.hex()}${dk.hex()}"


def verify_password(password: str, hashed: str | None) -> bool:
    """Verify plain password against stored hash."""
    if not hashed:
        return False
    try:
        parts = hashed.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        rounds = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected = bytes.fromhex(parts[3])
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False
