from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from typing import Any

import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _use_direct_bcrypt() -> bool:
    return version("bcrypt").split(".", maxsplit=1)[0] >= "5"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if _use_direct_bcrypt():
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (AttributeError, ValueError):
        # passlib 1.7.4 can fail during bcrypt backend probing with bcrypt>=5.
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password cannot be longer than 72 bytes with bcrypt")
    if _use_direct_bcrypt():
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    try:
        return pwd_context.hash(password)
    except (AttributeError, ValueError):
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _create_token(subject: str, role: str, token_type: str, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {"sub": subject, "role": role, "exp": expire, "type": token_type}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str, role: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return _create_token(subject, role, "access", expire - datetime.now(timezone.utc))

def create_refresh_token(subject: str, role: str, expires_delta: timedelta | None = None) -> str:
    return _create_token(
        subject,
        role,
        "refresh",
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    token_type = payload.get("type")
    if expected_type and token_type != expected_type:
        raise ValueError("Invalid token")
    return payload
