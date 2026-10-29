from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.core.enums import CandidateStatus, ExamPhase, ExamType, RequestStatus, RequestType


class BatchCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    name: str = Field(min_length=1, max_length=150)
    owner_id: str | None = None
    phase: str = Field(min_length=1, max_length=100)


class YearPhaseCardCreate(BaseModel):
    phase: str = Field(min_length=1, max_length=100)
    candidate_emails_csv: str | None = None


class CandidateEmailsImportRequest(BaseModel):
    emails_csv: str = Field(min_length=3)


class BatchOwnerAssignRequest(BaseModel):
    owner_id: str = Field(min_length=1)


class PhaseBatchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    owner_id: str = Field(min_length=1)


class BatchDetailsUpdate(BaseModel):
    start_date: date
    end_date: date
    tech_stack: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dates(self) -> "BatchDetailsUpdate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class BatchOut(BaseModel):
    id: str
    year: int
    name: str
    owner_id: str | None = None
    owner_name: str | None = None
    phase: str
    start_date: date | None = None
    end_date: date | None = None
    tech_stack: list[str] = []
    created_at: datetime
    updated_at: datetime


class CandidateImportSkipOut(BaseModel):
    email: EmailStr
    reason: str


class CandidateEmailsImportResult(BaseModel):
    year: int | None = None
    phase: str | None = None
    batch_id: str | None = None
    processed_emails: int
    created_candidates: int = 0
    updated_candidates: int = 0
    assigned: int = 0
    skipped: list[CandidateImportSkipOut] = []


class YearPhaseOut(BaseModel):
    id: str
    year: int
    phase: str
    status: str
    candidate_count: int
    unassigned_candidate_count: int
    batch_count: int
    batches: list[BatchOut] = []
    created_at: datetime
    updated_at: datetime


class CandidateCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=150)
    eligible_phase: str = Field(min_length=1, max_length=100)
    college: str | None = None
    graduation_year: int | None = None
    tech_stack: str | None = None
    percentage: float | None = Field(default=None, ge=0, le=100)
    intake_year: int | None = Field(default=None, ge=2000, le=2100)
    offer_accepted: bool = False


class CandidateEmailImportRequest(BaseModel):
    emails_csv: str = Field(min_length=3)


class CandidateAssignRequest(BaseModel):
    candidate_ids: list[str] = Field(min_length=1)


class CandidateEmploymentUpdate(BaseModel):
    uid: str = Field(min_length=1, max_length=100)
    employee_email: EmailStr


class CandidateOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    eligible_phase: str
    intake_year: int | None = None
    college: str | None = None
    graduation_year: int | None = None
    tech_stack: str | None = None
    percentage: float | None = None
    batch_id: str | None = None
    uid: str | None = None
    employee_email: EmailStr | None = None
    offer_accepted: bool = False
    source: str | None = None
    status: CandidateStatus
    pre_onboarding_score: float | None = None
    post_onboarding_score: float | None = None
    knowledge_check_python_score: float | None = None
    knowledge_check_java_score: float | None = None
    marks: dict[str, float] = {}
    alternate_emails: list[str] = []
    baseline_data: dict[str, Any] = {}
    baseline_email_map: dict[str, Any] = {}
    updated_at: datetime
    created_at: datetime


class CandidateSearchFilters(BaseModel):
    q: str | None = None
    status: CandidateStatus | None = None
    tech_stack: str | None = None
    college: str | None = None
    eligible_phase: str | None = None


class MarksUpdate(BaseModel):
    marks: dict[str, float] = Field(min_length=1)


class ExamScoreInput(BaseModel):
    candidate_id: str
    phase: ExamPhase
    exam_type: ExamType
    custom_exam_name: str | None = Field(default=None, max_length=150)
    attempt: int = Field(ge=1, le=2)
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    pass_percentage: float = Field(default=60, ge=0, le=100)

    @model_validator(mode="after")
    def validate_custom_exam_name(self) -> "ExamScoreInput":
        if self.exam_type == ExamType.CUSTOM_EXAM and not self.custom_exam_name:
            raise ValueError("custom_exam_name is required for CUSTOM_EXAM")
        return self


class ExamResultOut(BaseModel):
    id: str
    candidate_id: str
    batch_id: str | None = None
    phase: ExamPhase
    exam_type: ExamType
    exam_name: str
    attempt: int
    score: float
    max_score: float
    passed: bool
    candidate_status_after: CandidateStatus
    timeline_badge: str | None = None
    created_by: str
    created_at: datetime


class TimelineEventOut(BaseModel):
    id: str
    candidate_id: str
    actor_id: str
    event_type: str
    description: str
    metadata: dict = {}
    created_at: datetime


class ChangeRequestCreate(BaseModel):
    candidate_email: EmailStr
    request_type: RequestType
    reason: str = Field(min_length=5, max_length=1000)


class RuleChangeRequestCreate(BaseModel):
    batch_id: str = Field(description="Batch for which the configuration rule change is requested")
    exam_type: ExamType = Field(description="Exam or assessment for which the pass rule change is requested")
    custom_exam_name: str | None = Field(
        default=None,
        max_length=150,
        description="Required when exam_type is CUSTOM_EXAM",
        examples=["DSA Round 1"],
    )
    current_pass_percentage: float = Field(
        ge=0,
        le=100,
        description="Current pass percentage configured for this batch",
        examples=[60],
    )
    requested_pass_percentage: float = Field(
        ge=0,
        le=100,
        description="Requested pass percentage for this batch",
        examples=[70],
    )
    reason: str = Field(
        min_length=5,
        max_length=1000,
        description="Why this configuration rule change is required",
        examples=["Need to update the evaluation rule for this batch."],
    )

    @model_validator(mode="after")
    def validate_custom_exam_name(self) -> "RuleChangeRequestCreate":
        if self.exam_type == ExamType.CUSTOM_EXAM and not self.custom_exam_name:
            raise ValueError("custom_exam_name is required for CUSTOM_EXAM")
        return self


class ChangeRequestReview(BaseModel):
    status: RequestStatus
    reviewer_comment: str | None = Field(default=None, max_length=1000)


class ChangeRequestOut(BaseModel):
    id: str
    candidate_id: str | None = None
    candidate_email: EmailStr | None = None
    batch_id: str | None = None
    requested_by: str
    request_type: RequestType
    exam_type: ExamType | None = None
    custom_exam_name: str | None = None
    reason: str
    current_pass_percentage: float | None = None
    requested_pass_percentage: float | None = None
    status: RequestStatus
    reviewer_id: str | None = None
    reviewer_comment: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None


class YearCardOut(BaseModel):
    year: int
    status: str
    candidate_count: int
    batch_count: int
    phases_created: list[str] = []
    phases: list[YearPhaseOut] = []
    batches: list[BatchOut] = []


class YearGridOut(BaseModel):
    reference_year: int
    active_year: YearCardOut | None = None
    completed_year: YearCardOut | None = None
    archive_years: list[YearCardOut] = []


class YearFilterOptionsOut(BaseModel):
    phases: list[str] = []
    candidate_statuses: list[CandidateStatus] = []
    colleges: list[str] = []
    tech_stacks: list[str] = []


class YearArchiveOut(BaseModel):
    year: int
    status: str
    candidate_count: int
    batch_count: int
    filters: YearFilterOptionsOut
    candidates: list[CandidateOut]
    batches: list[BatchOut]
