from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import KNOWN_EVENTS, LOGIN_FAILED, LOGIN_SUCCESS, SIGNAL_EVENTS
from app.config import get_settings
from app.database import get_db
from app.deps import active_session_count, get_current_user, require_roles
from app.models import AuditLog, User
from app.schemas import AuditOut, DashboardOut, EventCount, SecuritySettingsOut
from app.security import utcnow

router = APIRouter(tags=["security"])
settings = get_settings()


def _recent(db: Session, *, limit: int, event_type: str | None = None, event_types: set[str] | None = None, actor: User | None = None, personal: bool = False):
    stmt = select(AuditLog)
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if event_types:
        stmt = stmt.where(AuditLog.event_type.in_(event_types))
    if personal and actor is not None:
        stmt = stmt.where(or_(AuditLog.user_id == actor.id, AuditLog.subject == actor.email))
    stmt = stmt.order_by(AuditLog.id.desc()).limit(limit)
    return list(db.scalars(stmt))


def _count(db: Session, stmt) -> int:
    return int(db.scalar(stmt) or 0)


@router.get("/api/dashboard", response_model=DashboardOut)
def dashboard(actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    personal = actor.role == "user"
    cutoff = utcnow() - timedelta(hours=24)
    scope_filter = []
    if personal:
        scope_filter.append(or_(AuditLog.user_id == actor.id, AuditLog.subject == actor.email))

    failed_stmt = select(func.count()).select_from(AuditLog).where(
        AuditLog.event_type == LOGIN_FAILED,
        AuditLog.created_at >= cutoff,
        *scope_filter,
    )
    signal_stmt = select(func.count()).select_from(AuditLog).where(
        AuditLog.event_type.in_(SIGNAL_EVENTS),
        AuditLog.created_at >= cutoff,
        *scope_filter,
    )
    counts_stmt = select(AuditLog.event_type, func.count()).group_by(AuditLog.event_type)
    if personal:
        counts_stmt = counts_stmt.where(or_(AuditLog.user_id == actor.id, AuditLog.subject == actor.email))

    event_counts = [
        EventCount(event_type=event_type, count=count)
        for event_type, count in db.execute(counts_stmt).all()
    ]
    return DashboardOut(
        scope="personal" if personal else "organization",
        total_users=None if personal else _count(db, select(func.count()).select_from(User)),
        active_sessions=active_session_count(db, actor.id if personal else None),
        failed_logins_24h=_count(db, failed_stmt),
        security_events_24h=_count(db, signal_stmt),
        recent_logins=[AuditOut.model_validate(row) for row in _recent(db, limit=8, event_type=LOGIN_SUCCESS, actor=actor, personal=personal)],
        recent_failures=[AuditOut.model_validate(row) for row in _recent(db, limit=8, event_type=LOGIN_FAILED, actor=actor, personal=personal)],
        recent_events=[AuditOut.model_validate(row) for row in _recent(db, limit=8, event_types=SIGNAL_EVENTS, actor=actor, personal=personal)],
        recent_audit=[AuditOut.model_validate(row) for row in _recent(db, limit=8, actor=actor, personal=personal)],
        event_counts=event_counts,
    )


@router.get("/api/logs", response_model=list[AuditOut])
def logs(
    event_type: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_roles("admin", "analyst")),
    db: Session = Depends(get_db),
):
    if event_type is not None and event_type not in KNOWN_EVENTS:
        raise HTTPException(status_code=422, detail="Unknown event type")
    return _recent(db, limit=limit, event_type=event_type)


@router.get("/api/settings/security", response_model=SecuritySettingsOut)
def security_settings(_: User = Depends(get_current_user)):
    return SecuritySettingsOut(
        environment=settings.environment,
        access_token_minutes=settings.access_token_minutes,
        cookie_secure=settings.cookie_secure,
        password_min_length=settings.password_min_length,
        rate_limit_login=settings.rate_limit_login,
        rate_limit_window_seconds=settings.rate_limit_window_seconds,
        enable_docs=settings.enable_docs,
        trust_proxy=settings.trust_proxy,
        security_headers=[
            "Content-Security-Policy",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy",
            "Permissions-Policy",
            "Cache-Control",
        ],
    )
