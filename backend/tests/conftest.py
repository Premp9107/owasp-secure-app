import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-key-not-for-production-use"
os.environ["SEED_DEMO_USERS"] = "false"
os.environ["RATE_LIMIT_LOGIN"] = "5"
os.environ["RATE_LIMIT_REGISTER"] = "50"
os.environ["ENVIRONMENT"] = "development"
os.environ["ENABLE_DOCS"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import limiter


@pytest.fixture()
def client():
    limiter.reset()
    with TestClient(app) as test_client:
        yield test_client


def csrf_headers(test_client: TestClient) -> dict[str, str]:
    token = test_client.cookies.get("csrf_token")
    assert token, "expected a CSRF cookie after authentication"
    return {"X-CSRF-Token": token}


def register(test_client: TestClient, email: str, password: str = "ValidPass!234", full_name: str = "Test User"):
    response = test_client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    return response
