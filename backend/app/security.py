"""Password hashing, JWT creation, and small input helpers.

Queries go through SQLAlchemy bound parameters. This module never builds SQL.
"""

import re
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from app.config import get_settings

settings = get_settings()

# OWASP-aligned Argon2id parameters for an interactive login (demo-friendly).
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
_dummy_hash: str | None = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def dummy_password_hash() -> str:
    """Used when the account does not exist so login timing stays similar."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("NotARealAccount!234")
    return _dummy_hash


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def validate_password_strength(password: str) -> None:
    if not isinstance(password, str):
        raise ValueError("Password is required")
    if len(password) < settings.password_min_length or len(password) > 128:
        raise ValueError(f"Password must be {settings.password_min_length} to 128 characters")
    if password.strip() != password or any(char.isspace() for char in password):
        raise ValueError("Password must not contain spaces")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must include a lowercase letter")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must include an uppercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must include a digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("Password must include a symbol")


def clean_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) < 2 or len(cleaned) > 80:
        raise ValueError("Name must be 2 to 80 characters")
    if re.search(r"[\x00-\x1f]", cleaned):
        raise ValueError("Name contains invalid control characters")
    return cleaned


def create_access_token(*, user_id: int, role: str, minutes: int | None = None) -> tuple[str, str, datetime]:
    lifetime = settings.access_token_minutes if minutes is None else minutes
    issued = utcnow()
    expires = issued + timedelta(minutes=lifetime)
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": jti,
        "iat": issued,
        "exp": expires,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti, expires


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def token_error_is_expiry(exc: Exception) -> bool:
    return isinstance(exc, jwt.ExpiredSignatureError)
