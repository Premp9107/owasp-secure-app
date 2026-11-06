"""Runtime settings. Secrets come from the environment, never from source."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE = "sqlite:///" + (BACKEND_DIR / "aegis.db").as_posix()


class Settings(BaseSettings):
    database_url: str = DEFAULT_SQLITE
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    environment: str = "development"
    cookie_secure: bool = False
    seed_demo_users: bool = True
    rate_limit_login: int = 5
    rate_limit_register: int = 20
    rate_limit_window_seconds: int = 900
    enable_docs: bool = True
    trust_proxy: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    password_min_length: int = Field(default=12)

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @model_validator(mode="after")
    def enforce_production_rules(self):
        self.assert_production_safe()
        return self

    def assert_production_safe(self) -> None:
        if self.environment.lower() == "production":
            if self.jwt_secret in {"", "dev-only-change-me", "replace-with-a-long-random-string"}:
                raise RuntimeError("Set a unique JWT_SECRET before running with ENVIRONMENT=production")
            if len(self.jwt_secret) < 32:
                raise RuntimeError("JWT_SECRET must be at least 32 characters in production")
            if not self.cookie_secure:
                raise RuntimeError("COOKIE_SECURE must be true in production")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.assert_production_safe()
    return settings
