from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import LOGIN_FAILED, LOGIN_SUCCESS, LOGOUT, RATE_LIMITED, REGISTER, record_event
from app.config import get_settings
from app.database import get_db
from app.deps import (
    active_session_count,
    clear_auth_cookies,
    enforce_csrf,
    get_current_user,
    set_auth_cookies,
)
from app.models import SessionToken, User
from app.rate_limit import limiter
from app.schemas import AuthUserOut, LoginIn, MeOut, RegisterIn, UserOut
from app.security import (
    create_access_token,
    dummy_password_hash,
    hash_password,
    utcnow,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()
GENERIC_LOGIN = "Invalid email or password"
GENERIC_REGISTER = "Unable to create an account with those details"


def _issue_session(db: Session, request: Request, response: Response, user: User) -> AuthUserOut:
    token, jti, expires = create_access_token(user_id=user.id, role=user.role)
    max_age = settings.access_token_minutes * 60
    db.add(
        SessionToken(
            user_id=user.id,
            jti=jti,
            ip_address=request.client.host[:64] if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:255],
            expires_at=expires,
        )
    )
    record_event(
        db,
        event_type=LOGIN_SUCCESS,
        message="Successful login",
        request=request,
        user_id=user.id,
        subject=user.email,
        commit=False,
    )
    db.commit()
    set_auth_cookies(response, token, max_age)
    return AuthUserOut(user=UserOut.model_validate(user), expires_in=max_age, session_expires_at=expires)


@router.post("/register", response_model=AuthUserOut, status_code=201)
def register(payload: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip_key = f"register:ip:{request.client.host if request.client else 'unknown'}"
    if limiter.is_blocked(ip_key, settings.rate_limit_register, settings.rate_limit_window_seconds):
        record_event(db, event_type=RATE_LIMITED, message="Registration rate limit reached", request=request)
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
    limiter.record(ip_key)

    email = payload.email.lower()
    if payload.password.lower() == email:
        raise HTTPException(status_code=422, detail="Password must not match the email address")
    if db.scalar(select(User).where(User.email == email)):
        record_event(
            db,
            event_type=REGISTER,
            message="Registration rejected",
            request=request,
            subject=email,
        )
        raise HTTPException(status_code=400, detail=GENERIC_REGISTER)

    user = User(email=email, full_name=payload.full_name, password_hash=hash_password(payload.password), role="user")
    db.add(user)
    db.flush()
    record_event(
        db,
        event_type=REGISTER,
        message="Account registered",
        request=request,
        user_id=user.id,
        subject=user.email,
        commit=False,
    )
    db.commit()
    db.refresh(user)
    return _issue_session(db, request, response, user)


@router.post("/login", response_model=AuthUserOut)
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower()
    host = request.client.host if request.client else "unknown"
    ip_key = f"login:ip:{host}"
    email_key = f"login:email:{email}"
    window = settings.rate_limit_window_seconds
    limit = settings.rate_limit_login
    if limiter.is_blocked(ip_key, limit, window) or limiter.is_blocked(email_key, limit, window):
        record_event(
            db,
            event_type=RATE_LIMITED,
            message="Login rate limit reached",
            request=request,
            subject=email,
        )
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later.", headers={"Retry-After": str(window)})

    user = db.scalar(select(User).where(User.email == email))
    password_ok = verify_password(payload.password, user.password_hash if user else dummy_password_hash())
    if user is None or not user.is_active or not password_ok:
        limiter.record(ip_key)
        limiter.record(email_key)
        record_event(
            db,
            event_type=LOGIN_FAILED,
            message="Failed login attempt",
            request=request,
            user_id=user.id if user else None,
            subject=email,
        )
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN)

    limiter.clear_key(email_key)
    return _issue_session(db, request, response, user)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(enforce_csrf),
):
    jti = getattr(request.state, "jti", None)
    row = db.scalar(select(SessionToken).where(SessionToken.jti == jti)) if jti else None
    if row and row.revoked_at is None:
        row.revoked_at = utcnow()
    record_event(
        db,
        event_type=LOGOUT,
        message="Logout",
        request=request,
        user_id=user.id,
        subject=user.email,
        commit=False,
    )
    db.commit()
    clear_auth_cookies(response)
    return {"detail": "Logged out"}


@router.get("/me", response_model=MeOut)
def me(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MeOut(
        user=UserOut.model_validate(user),
        session_expires_at=request.state.session_expires_at,
        active_sessions=active_session_count(db, user.id),
    )


@router.post("/revoke-other-sessions")
def revoke_other_sessions(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(enforce_csrf),
):
    revoke_sessions(db, user.id, keep_jti=request.state.jti)
    record_event(
        db,
        event_type=LOGOUT,
        message="Other sessions revoked",
        request=request,
        user_id=user.id,
        subject=user.email,
        commit=False,
    )
    db.commit()
    return {"detail": "Other sessions were revoked"}
