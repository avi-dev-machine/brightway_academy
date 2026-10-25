"""Health checks, authentication, error envelope and middleware behaviour."""

from tests.factories import auth_header, make_token, make_user


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"status": "ok"}}
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_health_db_and_storage(client):
    assert client.get("/health/db").json()["data"]["status"] == "ok"
    body = client.get("/health/storage").json()
    assert body["data"] == {"status": "ok", "backend": "local"}


def test_incoming_request_id_is_echoed(client):
    response = client.get("/health", headers={"X-Request-ID": "req-12345678"})
    assert response.headers["X-Request-ID"] == "req-12345678"


def test_unauthenticated_request_is_rejected(client):
    response = client.get("/api/v1/students")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_malformed_and_expired_tokens_are_rejected(client, admin_id):
    bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "INVALID_TOKEN"
    expired = make_token(admin_id, expires_in=-120)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_valid_token_without_profile_is_forbidden(client):
    from uuid import uuid4

    response = client.get("/api/v1/auth/me", headers=auth_header(uuid4()))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_PROVISIONED"


def test_disabled_account_is_forbidden(client, db):
    user_id = make_user(db, "ADMIN", active=False)
    response = client.get("/api/v1/auth/me", headers=auth_header(user_id))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"


def test_me_returns_role_and_display_name(client, student, student_headers):
    response = client.get("/api/v1/auth/me", headers=student_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["role"] == "STUDENT"
    assert data["display_name"] == "Asha Roy"
    assert data["student_id"] == str(student["id"])


def test_validation_errors_use_the_envelope(client, admin_headers):
    response = client.post("/api/v1/courses", json={"code": "", "name": ""}, headers=admin_headers)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert {d["field"] for d in error["details"]} >= {"body.code", "body.name"}


def test_unknown_route_uses_the_envelope(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_openapi_docs_available_outside_production(client):
    assert client.get("/openapi.json").status_code == 200
