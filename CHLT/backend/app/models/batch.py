from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PhaseName = Literal["pre_onboarding", "post_onboarding"]


class BatchBase(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    phase: PhaseName
    name: str = Field(..., min_length=2, max_length=100)
    tech_stack: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    owner_id: str | None = None
    is_active: bool = True


class BatchCreate(BatchBase):
    pass


class BatchUpdate(BaseModel):
    tech_stack: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    owner_id: str | None = None
    is_active: bool | None = None


class BatchAssignCandidatesRequest(BaseModel):
    candidate_ids: list[str] = Field(default_factory=list)


class BatchOut(BatchBase):
    id: str
    owner_name: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
