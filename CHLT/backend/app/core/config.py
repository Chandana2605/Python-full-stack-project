from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "L&D Management Backend"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    secret_key: str = Field(..., min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "ld_management"
    admin_name: str = "L&D Manager"
    admin_email: str = "admin@company.local"
    admin_employee_id: str = "ADMIN001"
    admin_temporary_password: str = "ChangeMe123!"
    frontend_login_url: str = "http://localhost:3000/login"
    smtp_enabled: bool = False
    smtp_host: str = "smtp.office365.com"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_sender_email: str = "no-reply@company.local"
    smtp_sender_name: str = "L&D Management Platform"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"false", "0", "no", "off", "release", "production"}:
                return False
        return bool(value)


@lru_cache
def get_settings() -> Settings:
    return Settings()
