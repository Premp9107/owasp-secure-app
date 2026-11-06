"""Local demonstration accounts. Passwords exist only to seed a fresh database."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.security import hash_password

settings = get_settings()

DEMO_USERS = (
    ("admin@example.com", "Avery Quinn", "VigilAdmin!234", "admin"),
    ("analyst@example.com", "Riley Chen", "VigilAnalyst!234", "analyst"),
    ("user@example.com", "Jordan Hale", "VigilUser!234", "user"),
)


def seed_demo_users(db: Session) -> None:
    if not settings.seed_demo_users:
        return
    existing = db.scalar(select(User.id).limit(1))
    if existing is not None:
        return
    for email, full_name, password, role in DEMO_USERS:
        db.add(
            User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                role=role,
                is_active=True,
            )
        )
    db.commit()
