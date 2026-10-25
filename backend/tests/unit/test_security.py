from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.security import TokenVerifier
from app.exceptions import UnauthorizedError
from tests.factories import SIGNING_KEY, TEST_ISSUER, make_token

verifier = TokenVerifier(issuer=TEST_ISSUER, key_resolver=lambda _t: SIGNING_KEY.public_key())


def code_of(token: str) -> str:
    with pytest.raises(UnauthorizedError) as info:
        verifier.verify(token)
    return info.value.code


def test_valid_token():
    user_id = uuid4()
    claims = verifier.verify(make_token(user_id, email="a@example.com"))
    assert claims.user_id == user_id
    assert claims.email == "a@example.com"


def test_expired_token():
    assert code_of(make_token(uuid4(), expires_in=-120)) == "TOKEN_EXPIRED"


@pytest.mark.parametrize(
    "token_kwargs",
    [
        {"issuer": "https://evil.example/auth/v1"},
        {"audience": "anon"},
        {"role": "anon"},
        {"is_anonymous": True},
        {"key": ec.generate_private_key(ec.SECP256R1())},  # signed by someone else
    ],
)
def test_rejected_tokens(token_kwargs):
    assert code_of(make_token(uuid4(), **token_kwargs)) == "INVALID_TOKEN"


def test_symmetric_algorithm_is_rejected():
    forged = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "iss": TEST_ISSUER,
            "role": "authenticated",
            "iat": 1,
            "exp": 4_102_444_800,
        },
        "guessed-secret",
        algorithm="HS256",
    )
    assert code_of(forged) == "INVALID_TOKEN"


def test_non_uuid_subject_is_rejected():
    assert code_of(make_token("not-a-uuid")) == "INVALID_TOKEN"  # type: ignore[arg-type]


def test_garbage_token():
    assert code_of("abc.def.ghi") == "INVALID_TOKEN"
