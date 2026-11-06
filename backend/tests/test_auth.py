from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password, verify_password
from tests.conftest import csrf_headers, register


def test_register_login_and_me(client):
    created = register(client, "ada@example.com", full_name="Ada Lovelace")
    assert created.status_code == 201
    body = created.json()
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["role"] == "user"
    assert "password" not in body["user"]
    assert client.cookies.get("access_token")
    assert "access_token" not in created.text

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["full_name"] == "Ada Lovelace"

    client.post("/api/auth/logout", headers=csrf_headers(client))
    fresh = client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": "ValidPass!234"},
    )
    assert fresh.status_code == 200
    assert fresh.json()["user"]["role"] == "user"


def test_invalid_credentials_use_the_same_message(client):
    register(client, "known@example.com")
    client.post("/api/auth/logout", headers=csrf_headers(client))
    unknown = client.post("/api/auth/login", json={"email": "missing@example.com", "password": "ValidPass!234"})
    wrong = client.post("/api/auth/login", json={"email": "known@example.com", "password": "WrongPass!234"})
    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]
    assert "traceback" not in unknown.text.lower()


def test_weak_password_and_mass_assignment_rejected(client):
    weak = register(client, "weak@example.com", password="password")
    assert weak.status_code == 422
    extra = client.post(
        "/api/auth/register",
        json={
            "email": "root@example.com",
            "password": "ValidPass!234",
            "full_name": "Root User",
            "role": "admin",
        },
    )
    assert extra.status_code == 422
    db = SessionLocal()
    try:
        assert db.scalar(select(User).where(User.email == "root@example.com")) is None
    finally:
        db.close()


def test_password_hash_is_argon2():
    stored = hash_password("ValidPass!234")
    assert stored.startswith("$argon2")
    assert "ValidPass!234" not in stored
    assert verify_password("ValidPass!234", stored)
    assert not verify_password("OtherPass!234", stored)


def test_logout_revokes_the_session(client):
    register(client, "logout@example.com")
    token = client.cookies.get("access_token")
    response = client.post("/api/auth/logout", headers=csrf_headers(client))
    assert response.status_code == 200
    client.cookies.set("access_token", token)
    assert client.get("/api/auth/me").status_code == 401


def test_duplicate_registration_is_generic(client):
    assert register(client, "dup@example.com").status_code == 201
    client.post("/api/auth/logout", headers=csrf_headers(client))
    again = register(client, "dup@example.com")
    assert again.status_code == 400
    assert "exists" not in again.text.lower()
    assert "dup@example.com" not in again.text


def test_password_change_and_audit_redaction(client):
    register(client, "secret@example.com")
    changed = client.post(
        "/api/users/me/password",
        json={"current_password": "ValidPass!234", "new_password": "NewerPass!234"},
        headers=csrf_headers(client),
    )
    assert changed.status_code == 200
    client.post("/api/auth/logout", headers=csrf_headers(client))
    old = client.post("/api/auth/login", json={"email": "secret@example.com", "password": "ValidPass!234"})
    new = client.post("/api/auth/login", json={"email": "secret@example.com", "password": "NewerPass!234"})
    assert old.status_code == 401
    assert new.status_code == 200

    from app.models import AuditLog

    db = SessionLocal()
    try:
        blob = " ".join(row.message for row in db.scalars(select(AuditLog)))
    finally:
        db.close()
    assert "ValidPass!234" not in blob
    assert "NewerPass!234" not in blob
    assert "eyJ" not in blob
