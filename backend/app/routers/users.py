from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit import PASSWORD_CHANGE, ROLE_CHANGE, STATUS_CHANGE, UNAUTHORIZED, record_event
from app.database import get_db
from app.deps import enforce_csrf, get_current_user, require_roles, revoke_sessions
from app.models import ROLES, User
from app.schemas import PasswordChange, ProfileUpdate, RoleUpdate, StatusUpdate, UserOut
from app.security import hash_password, validate_password_strength, verify_password

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(enforce_csrf)])


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _load_visible(db: Session, request: Request, actor: User, user_id: int) -> User:
    target = db.get(User, user_id)
    if actor.role in {"admin", "analyst"}:
        if target is None:
            raise HTTPException(status_code=404, detail="Resource not found")
        return target
    if target is None or target.id != actor.id:
        record_event(
            db,
            event_type=UNAUTHORIZED,
            message=f"User {actor.id} attempted to open another account",
            request=request,
            user_id=actor.id,
            subject=actor.email,
        )
        raise HTTPException(status_code=404, detail="Resource not found")
    return target


@router.get("", response_model=list[UserOut])
def list_users(
    request: Request,
    q: str | None = Query(default=None, max_length=200),
    actor: User = Depends(require_roles("admin", "analyst")),
    db: Session = Depends(get_db),
):
    stmt = select(User)
    if q:
        term = _like(q.strip())
        stmt = stmt.where(or_(User.email.ilike(term, escape="\\"), User.full_name.ilike(term, escape="\\")))
    stmt = stmt.order_by(User.id.asc()).limit(100)
    return list(db.scalars(stmt))


@router.get("/me", response_model=UserOut)
def own_profile(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.full_name = payload.full_name
    record_event(
        db,
        event_type=STATUS_CHANGE,
        message="Profile name updated",
        request=request,
        user_id=user.id,
        subject=user.email,
        commit=False,
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/password")
def change_password(
    payload: PasswordChange,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=422, detail="Choose a different password")
    if payload.new_password.lower() == user.email.lower():
        raise HTTPException(status_code=422, detail="Password must not match the email address")
    validate_password_strength(payload.new_password)
    user.password_hash = hash_password(payload.new_password)
    revoke_sessions(db, user.id, keep_jti=getattr(request.state, "jti", None))
    record_event(
        db,
        event_type=PASSWORD_CHANGE,
        message="Password changed",
        request=request,
        user_id=user.id,
        subject=user.email,
        commit=False,
    )
    db.commit()
    return {"detail": "Password updated"}


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    request: Request,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _load_visible(db, request, actor, user_id)


@router.patch("/{user_id}/role", response_model=UserOut)
def change_role(
    user_id: int,
    payload: RoleUpdate,
    request: Request,
    actor: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    if payload.role not in ROLES:
        raise HTTPException(status_code=422, detail="Unknown role")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    if target.id == actor.id:
        raise HTTPException(status_code=400, detail="You cannot change your own role")
    if target.role == "admin" and payload.role != "admin":
        other_admins = db.scalar(select(User).where(User.role == "admin", User.id != target.id, User.is_active.is_(True)))
        if other_admins is None:
            raise HTTPException(status_code=400, detail="The last active administrator cannot be demoted")
    previous = target.role
    target.role = payload.role
    revoke_sessions(db, target.id)
    record_event(
        db,
        event_type=ROLE_CHANGE,
        message=f"Role changed from {previous} to {payload.role} for user {target.id}",
        request=request,
        user_id=actor.id,
        subject=target.email,
        commit=False,
    )
    db.commit()
    db.refresh(target)
    return target


@router.patch("/{user_id}/status", response_model=UserOut)
def change_status(
    user_id: int,
    payload: StatusUpdate,
    request: Request,
    actor: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    if target.id == actor.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    target.is_active = payload.is_active
    if not payload.is_active:
        revoke_sessions(db, target.id)
    record_event(
        db,
        event_type=STATUS_CHANGE,
        message=f"Account {'enabled' if payload.is_active else 'disabled'} for user {target.id}",
        request=request,
        user_id=actor.id,
        subject=target.email,
        commit=False,
    )
    db.commit()
    db.refresh(target)
    return target
