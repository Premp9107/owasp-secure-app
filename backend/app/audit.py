"""Security audit trail.

Messages are short operational notes. Callers must not pass passwords, tokens,
or authorization headers.
"""

from fastapi import Request

from app.config import get_settings
from app.models import AuditLog

settings = get_settings()

LOGIN_SUCCESS = "login_success"
LOGIN_FAILED = "login_failed"
LOGOUT = "logout"
REGISTER = "register"
PASSWORD_CHANGE = "password_change"
ROLE_CHANGE = "role_change"
STATUS_CHANGE = "status_change"
UNAUTHORIZED = "unauthorized"
RATE_LIMITED = "rate_limited"

KNOWN_EVENTS = {
    LOGIN_SUCCESS,
    LOGIN_FAILED,
    LOGOUT,
    REGISTER,
    PASSWORD_CHANGE,
    ROLE_CHANGE,
    STATUS_CHANGE,
    UNAUTHORIZED,
    RATE_LIMITED,
}

SIGNAL_EVENTS = {
    LOGIN_FAILED,
    UNAUTHORIZED,
    RATE_LIMITED,
    ROLE_CHANGE,
    PASSWORD_CHANGE,
    STATUS_CHANGE,
}


def client_ip(request: Request) -> str:
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
    if request.client and request.client.host:
        return request.client.host[:64]
    return "unknown"


def user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")[:255]


def _safe_message(message: str) -> str:
    lowered = message.lower()
    if "password" in lowered or "bearer " in lowered or "eyj" in lowered:
        return "Security event recorded"
    return message[:500]


def record_event(
    db,
    *,
    event_type: str,
    message: str,
    request: Request,
    user_id: int | None = None,
    subject: str | None = None,
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        event_type=event_type,
        message=_safe_message(message),
        subject=(subject or None) and subject[:255],
        ip_address=client_ip(request),
        user_agent=user_agent(request),
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry
