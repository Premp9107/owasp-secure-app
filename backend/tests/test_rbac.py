from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog, User
from tests.conftest import csrf_headers, register


def _role(email: str, role: str) -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        user.role = role
        db.commit()
    finally:
        db.close()


def test_normal_user_cannot_open_admin_endpoints(client):
    register(client, "user-a@example.com")
    listing = client.get("/api/users")
    logs = client.get("/api/logs")
    role = client.patch("/api/users/1/role", json={"role": "admin"}, headers=csrf_headers(client))
    assert listing.status_code == 403
    assert logs.status_code == 403
    assert role.status_code == 403

    db = SessionLocal()
    try:
        denied = db.scalar(select(AuditLog).where(AuditLog.event_type == "unauthorized"))
        assert denied is not None
    finally:
        db.close()


def test_user_cannot_read_another_account(client):
    first = register(client, "owner@example.com")
    owner_id = first.json()["user"]["id"]
    other = ExtraClient()
    try:
        created = register(other.client, "other@example.com")
        other_id = created.json()["user"]["id"]
        hidden = client.get(f"/api/users/{other_id}")
        assert hidden.status_code == 404
        visible = other.client.get(f"/api/users/{owner_id}")
        assert visible.status_code == 404
        own = client.get("/api/users/me")
        assert own.status_code == 200
        assert own.json()["id"] == owner_id
    finally:
        other.close()


def test_analyst_can_read_but_not_change_roles(client):
    register(client, "analyst@example.com")
    _role("analyst@example.com", "analyst")
    register(client, "member@example.com")
    # Second registration replaced the session. Promote and log in as the analyst.
    client.post("/api/auth/logout", headers=csrf_headers(client))
    logged = client.post(
        "/api/auth/login",
        json={"email": "analyst@example.com", "password": "ValidPass!234"},
    )
    assert logged.status_code == 200
    assert client.get("/api/users").status_code == 200
    assert client.get("/api/logs").status_code == 200
    member_id = client.get("/api/users").json()[-1]["id"]
    denied = client.patch(
        f"/api/users/{member_id}/role",
        json={"role": "admin"},
        headers=csrf_headers(client),
    )
    assert denied.status_code == 403


def test_admin_role_change_rules(client):
    register(client, "admin@example.com", full_name="Admin User")
    _role("admin@example.com", "admin")
    client.post("/api/auth/logout", headers=csrf_headers(client))
    assert client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "ValidPass!234"},
    ).status_code == 200
    created = register(client, "promote@example.com")
    # Registration replaced the admin cookie, so sign the admin back in.
    client.post("/api/auth/logout", headers=csrf_headers(client))
    client.post("/api/auth/login", json={"email": "admin@example.com", "password": "ValidPass!234"})
    target_id = created.json()["user"]["id"]
    me = client.get("/api/auth/me").json()["user"]["id"]
    self_change = client.patch(f"/api/users/{me}/role", json={"role": "user"}, headers=csrf_headers(client))
    assert self_change.status_code == 400
    changed = client.patch(
        f"/api/users/{target_id}/role",
        json={"role": "analyst"},
        headers=csrf_headers(client),
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == "analyst"
    demote = client.patch(
        f"/api/users/{me}/role",
        json={"role": "user"},
        headers=csrf_headers(client),
    )
    assert demote.status_code == 400


class ExtraClient:
    def __init__(self):
        from fastapi.testclient import TestClient

        from app.main import app

        self._ctx = TestClient(app)
        self.client = self._ctx.__enter__()

    def close(self):
        self._ctx.__exit__(None, None, None)
