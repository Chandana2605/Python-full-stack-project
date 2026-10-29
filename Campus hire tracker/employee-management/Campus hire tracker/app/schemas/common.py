from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, EmailStr, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResolveMapping(BaseModel):
    row: int
    candidate_id: str | None = None
    mapped_email: EmailStr | None = None
    selected_index: int | None = None


class SimpleResolveRequest(BaseModel):
    resolve_all: bool = False
    rows: list[int] = Field(default_factory=list)
    row_mappings: list[ResolveMapping] = Field(default_factory=list)


class AutoResolveRequest(BaseModel):
    resolve_all: bool = True
