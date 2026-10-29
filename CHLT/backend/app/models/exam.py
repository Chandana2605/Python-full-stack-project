from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ExamType = Literal["baseline", "knowledge_check"]
ExamStatus = Literal["attended", "not_attended", "passed", "failed"]
CandidateBadge = Literal[
    "eligible_for_offer",
    "recommended_loi_cancellation",
    "deployment_ready",
    "referred_to_hr",
]


class ExamBase(BaseModel):
    candidate_id: str
    exam_type: ExamType
    coding_name: str | None = Field(default=None, max_length=100)
    score: float | None = None
    attended: bool = True
    passed: bool = False
    attempt_number: int = Field(default=1, ge=1, le=10)
    status: ExamStatus


class ExamCreate(ExamBase):
    batch_id: str | None = None


class ExamUpdate(BaseModel):
    score: float | None = None
    attended: bool | None = None
    passed: bool | None = None
    status: ExamStatus | None = None


class ExamOut(ExamBase):
    id: str
    batch_id: str | None = None
    badge: CandidateBadge | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
