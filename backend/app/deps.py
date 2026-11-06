import secrets

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import UNAUTHORIZED, client_ip, record_event
from app.config import get_settings
from app.database import get_db
from app.models import SessionToken, User
from jwt import InvalidTokenError

from app.security import decode_access_token, token_error_is_expiry, utcnow

settings = get_settings()


def _unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def read_bearer(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if header is None:
        return None
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        raise _unauthorized("Authentication required")
    return value.strip()


def enforce_csrf(request: Request) -> None:
    """Double-submit cookie check for browser sessions.

    Bearer tokens are not sent automatically by browsers, so CSRF does not apply
    to a request that explicitly presents Authorization. Cookie-authenticated
    unsafe requests must echo the non-HttpOnly csrf_token cookie.
    """
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if read_bearer(request):
        return
    if not request.cookies.get("access_token"):
        return
    cookie = request.cookies.get("csrf_token", "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not header or len(cookie) != len(header) or not secrets.compare_digest(cookie, header):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


def set_auth_cookies(response: Response, token: str, max_age: int) -> str:
    csrf = secrets.token_urlsafe(32)
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return csrf


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/", samesite="lax", secure=settings.cookie_secure)
    response.delete_cookie("csrf_token", path="/", samesite="lax", secure=settings.cookie_secure)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = read_bearer(request) or request.cookies.get("access_token")
    if not token:
        raise _unauthorized()
    try:
        payload = decode_access_token(token)
    except InvalidTokenError as exc:
        detail = "Session expired" if token_error_is_expiry(exc) else "Authentication required"
        raise _unauthorized(detail) from None

    jti = payload.get("jti")
    subject = payload.get("sub")
    if not jti or not subject:
        raise _unauthorized()
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _unauthorized() from None

    session = db.scalar(select(SessionToken).where(SessionToken.jti == jti))
    now = utcnow()
    if session is None or session.revoked_at is not None or session.expires_at <= now or session.user_id != user_id:
        raise _unauthorized("Session is not active")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Authentication required")

    request.state.user_id = user.id
    request.state.jti = jti
    request.state.session_expires_at = session.expires_at
    return user


def require_roles(*roles: str):
    def checker(
        request: Request,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if user.role not in roles:
            record_event(
                db,
                event_type=UNAUTHORIZED,
                message=f"Role {user.role} was denied {request.method} {request.url.path}",
                request=request,
                user_id=user.id,
                subject=user.email,
            )
            raise HTTPException(status_code=403, detail="You do not have permission for this action")
        return user

    return checker


def active_session_count(db: Session, user_id: int | None = None) -> int:
    stmt = select(func.count()).select_from(SessionToken).where(
        SessionToken.revoked_at.is_(None),
        SessionToken.expires_at > utcnow(),
    )
    if user_id is not None:
        stmt = stmt.where(SessionToken.user_id == user_id)
    return int(db.scalar(stmt) or 0)


def revoke_sessions(db: Session, user_id: int, keep_jti: str | None = None) -> None:
    stmt = select(SessionToken).where(SessionToken.user_id == user_id, SessionToken.revoked_at.is_(None))
    for row in db.scalars(stmt):
        if keep_jti and row.jti == keep_jti:
            continue
        row.revoked_at = utcnow()
