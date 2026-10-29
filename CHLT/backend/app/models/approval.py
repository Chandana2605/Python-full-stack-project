from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ApprovalStatus = Literal["pending", "approved", "rejected"]


class ApprovalRequestCreate(BaseModel):
    target_type: str = Field(..., min_length=2, max_length=50)
    target_id: str | None = None
    title: str = Field(..., min_length=5, max_length=150)
    requested_change: str = Field(..., min_length=10, max_length=2000)
    proposed_value: str | None = Field(default=None, max_length=2000)


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str = Field(..., min_length=5, max_length=1000)


class RuleChangeRequestCreate(BaseModel):
    batch_id: str
    phase: str = Field(..., min_length=2, max_length=50)
    exam_name: str = Field(..., min_length=2, max_length=100)
    current_pass_percentage: float = Field(..., ge=0, le=100)
    requested_pass_percentage: float = Field(..., ge=0, le=100)
    reason: str = Field(..., min_length=5, max_length=1000)


class ApprovalOut(BaseModel):
    id: str
    target_type: str
    target_id: str | None = None
    title: str
    requested_change: str
    proposed_value: str | None = None
    status: ApprovalStatus
    requested_by: str
    reviewed_by: str | None = None
    review_reason: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
