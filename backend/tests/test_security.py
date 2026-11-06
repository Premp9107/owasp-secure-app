import jwt
import pytest

from app.config import Settings
from app.security import create_access_token
from tests.conftest import csrf_headers, register


def test_security_headers(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"


def test_sql_injection_search_stays_a_bound_filter(client):
    register(client, "alice@example.com", full_name="Alice Example")
    from app.database import SessionLocal
    from app.models import User
    from sqlalchemy import select

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "alice@example.com"))
        user.role = "analyst"
        db.commit()
    finally:
        db.close()
    client.post("/api/auth/logout", headers=csrf_headers(client))
    client.post("/api/auth/login", json={"email": "alice@example.com", "password": "ValidPass!234"})

    injected = client.get("/api/users", params={"q": "' OR 1=1 --"})
    assert injected.status_code == 200
    assert injected.json() == []
    matched = client.get("/api/users", params={"q": "alice@example.com"})
    assert matched.status_code == 200
    assert len(matched.json()) == 1
    assert "sqlite" not in injected.text.lower()
    assert "syntax" not in injected.text.lower()


def test_xss_payload_is_json_data(client):
    name = "Ada <script>alert(1)</script>"
    created = register(client, "xss@example.com", full_name=name)
    assert created.status_code == 201
    assert created.headers["content-type"].startswith("application/json")
    assert created.json()["user"]["full_name"] == name
    assert "<html" not in created.text.lower()


def test_tampered_and_expired_tokens_are_rejected(client):
    register(client, "token@example.com")
    token = client.cookies.get("access_token")
    header, payload, signature = token.split(".")
    bad_payload = ("A" if payload[0] != "A" else "B") + payload[1:]
    tampered = client.get("/api/auth/me", headers={"Authorization": f"Bearer {header}.{bad_payload}.{signature}"})
    assert tampered.status_code == 401

    expired, _, _ = create_access_token(user_id=1, role="user", minutes=-5)
    rejected = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert rejected.status_code == 401
    assert rejected.json()["detail"] == "Session expired"

    decoded = jwt.decode(token, "test-secret-key-not-for-production-use", algorithms=["HS256"])
    assert decoded["exp"] > decoded["iat"]


def test_login_rate_limit(client):
    for _ in range(5):
        response = client.post(
            "/api/auth/login",
            json={"email": "blocked@example.com", "password": "ValidPass!234"},
        )
        assert response.status_code == 401
    blocked = client.post(
        "/api/auth/login",
        json={"email": "blocked@example.com", "password": "ValidPass!234"},
    )
    assert blocked.status_code == 429
    assert "traceback" not in blocked.text.lower()


def test_cookie_session_requires_csrf(client):
    register(client, "csrf@example.com")
    blocked = client.post("/api/auth/logout")
    assert blocked.status_code == 403
    allowed = client.post("/api/auth/logout", headers=csrf_headers(client))
    assert allowed.status_code == 200


def test_validation_errors_do_not_leak_internals(client):
    response = client.post("/api/auth/login", json={"email": "not-an-email", "password": "x"})
    assert response.status_code == 422
    text = response.text.lower()
    assert "traceback" not in text
    assert "sqlalchemy" not in text
    assert "jwt_secret" not in text


def test_production_settings_reject_default_secret():
    with pytest.raises(RuntimeError):
        Settings(environment="production", jwt_secret="dev-only-change-me", cookie_secure=True)
