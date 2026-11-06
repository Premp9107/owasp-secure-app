from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.security import clean_name, validate_password_strength


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterIn(APIModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("full_name")
    @classmethod
    def name_ok(cls, value: str) -> str:
        return clean_name(value)

    @field_validator("password")
    @classmethod
    def password_ok(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class LoginIn(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdate(APIModel):
    full_name: str = Field(min_length=2, max_length=80)

    @field_validator("full_name")
    @classmethod
    def name_ok(cls, value: str) -> str:
        return clean_name(value)


class PasswordChange(APIModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_ok(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class RoleUpdate(APIModel):
    role: Literal["admin", "analyst", "user"]


class StatusUpdate(APIModel):
    is_active: bool


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class AuthUserOut(BaseModel):
    user: UserOut
    expires_in: int
    session_expires_at: datetime


class MeOut(BaseModel):
    user: UserOut
    session_expires_at: datetime
    active_sessions: int


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    event_type: str
    message: str
    subject: str | None
    ip_address: str | None
    created_at: datetime


class EventCount(BaseModel):
    event_type: str
    count: int


class DashboardOut(BaseModel):
    scope: Literal["personal", "organization"]
    total_users: int | None
    active_sessions: int
    failed_logins_24h: int
    security_events_24h: int
    recent_logins: list[AuditOut]
    recent_failures: list[AuditOut]
    recent_events: list[AuditOut]
    recent_audit: list[AuditOut]
    event_counts: list[EventCount]


class SecuritySettingsOut(BaseModel):
    environment: str
    access_token_minutes: int
    cookie_secure: bool
    password_min_length: int
    rate_limit_login: int
    rate_limit_window_seconds: int
    enable_docs: bool
    trust_proxy: bool
    security_headers: list[str]
