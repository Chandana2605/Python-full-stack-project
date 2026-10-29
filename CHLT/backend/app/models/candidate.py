from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


CandidateStatus = Literal[
    "master_imported",
    "pre_onboarding",
    "post_onboarding",
    "eligible_for_offer",
    "recommended_loi_cancellation",
    "deployment_ready",
    "referred_to_hr",
    "dropout_pending",
    "dropout_finalized",
    "resigned",
]


class CandidateBase(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    college: str | None = Field(default=None, max_length=200)
    percentage: float | None = Field(default=None, ge=0, le=100)


class CandidateCreate(CandidateBase):
    phase: str | None = None
    batch_id: str | None = None


class CandidateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    college: str | None = Field(default=None, max_length=200)
    percentage: float | None = Field(default=None, ge=0, le=100)
    phase: str | None = None
    batch_id: str | None = None
    status: CandidateStatus | None = None


class CandidateOut(CandidateBase):
    id: str
    phase: str | None = None
    batch_id: str | None = None
    status: CandidateStatus = "master_imported"
    offer_accepted: bool = False
    source: str = "master_database"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CandidateBulkCreateRequest(BaseModel):
    emails: list[EmailStr] = Field(default_factory=list)


class CandidateEmailImportRequest(BaseModel):
    emails_csv: str = Field(..., min_length=5, description="Comma-separated candidate emails")


class CandidateTimelineEvent(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str
    message: str
    created_by: str | None = None
    created_at: datetime | None = None
