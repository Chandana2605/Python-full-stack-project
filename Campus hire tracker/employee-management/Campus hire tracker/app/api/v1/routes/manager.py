from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.deps import require_roles
from app.core.enums import RequestStatus, Role
from app.schemas.auth import CurrentUser
from app.schemas.batches import (
    BatchOwnerAssignRequest,
    BatchOut,
    CandidateEmailsImportResult,
    CandidateEmailsImportRequest,
    CandidateCreate,
    CandidateOut,
    ChangeRequestOut,
    ChangeRequestReview,
    PhaseBatchCreate,
    RuleChangeRequestCreate,
    TimelineEventOut,
    YearPhaseCardCreate,
    YearPhaseOut,
    YearArchiveOut,
    YearCardOut,
    YearGridOut,
)
from app.schemas.common import AutoResolveRequest, SimpleResolveRequest
from app.schemas.users import UserCreate, UserOut
from app.services import baseline_service, batch_service, candidate_service, knowledge_service, request_service
from app.services.user_service import create_user, list_users

router = APIRouter()


@router.post("/candidates/upload")
async def upload_candidates(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await candidate_service.upload_candidates(file)


@router.post("/exams/baseline-upload")
async def upload_baseline(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await baseline_service.upload_baseline(file, user.id)


@router.post("/exams/baseline/resolve")
async def resolve_review(
    payload: AutoResolveRequest,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await baseline_service.resolve_mismatches(
        SimpleResolveRequest(resolve_all=payload.resolve_all), user.id
    )


@router.get("/search-candidates")
async def get_candidates(
    search: str = Query(None),
    min_score: float = Query(None),
    max_score: float = Query(None),
    attended: bool = Query(None),
    page: int = Query(1),
    limit: int = Query(10),
):
    return await candidate_service.get_candidates(
        search=search,
        min_score=min_score,
        max_score=max_score,
        attended=attended,
        page=page,
        limit=limit,
    )


@router.post("/exams/knowledge-check")
async def upload_knowledge_check(
    file: UploadFile,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await knowledge_service.upload_knowledge_check(file, user.id)


@router.post("/users", response_model=UserOut, summary="Create Batch Owner or Program Manager user")
async def create_platform_user(
    payload: UserCreate,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
) -> dict:
    return await create_user(payload, user.id)


@router.get("/users", response_model=list[UserOut], summary="List platform users")
async def read_platform_users(
    role: Role | None = Query(default=None),
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
) -> list[dict]:
    return await list_users(role)


@router.get("/batches/year-grid", response_model=YearGridOut, summary="View batch year grid for active, completed, and archive years")
async def read_batch_year_grid(
    reference_year: int | None = Query(default=None, ge=2000, le=2100),
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await batch_service.get_batch_grid(reference_year)


@router.get("/year-archives", response_model=list[YearCardOut], summary="View archived year cards for past years")
async def read_year_archives(
    reference_year: int | None = Query(default=None, ge=2000, le=2100),
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await batch_service.list_year_archives(reference_year)


@router.get("/year-archives/{year}", response_model=YearArchiveOut, summary="View historical data for a past year archive")
async def read_year_archive_history(
    year: int,
    q: str | None = Query(default=None),
    phase: str | None = Query(default=None),
    candidate_status: str | None = Query(default=None),
    tech_stack: str | None = Query(default=None),
    college: str | None = Query(default=None),
    reference_year: int | None = Query(default=None, ge=2000, le=2100),
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await batch_service.get_past_year_archive(
        year,
        q=q,
        phase=phase,
        candidate_status=candidate_status,
        tech_stack=tech_stack,
        college=college,
        reference_year=reference_year,
    )


@router.get("/batches/years/{year}", response_model=YearArchiveOut, summary="View yearly batch archive details with filters")
async def read_batch_year_details(
    year: int,
    q: str | None = Query(default=None),
    phase: str | None = Query(default=None),
    candidate_status: str | None = Query(default=None),
    tech_stack: str | None = Query(default=None),
    college: str | None = Query(default=None),
    reference_year: int | None = Query(default=None, ge=2000, le=2100),
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await batch_service.get_year_archive(
        year,
        q=q,
        phase=phase,
        candidate_status=candidate_status,
        tech_stack=tech_stack,
        college=college,
        reference_year=reference_year,
    )


@router.get("/batches/years/{year}/phases", response_model=YearCardOut, summary="View phase creation state for a specific year")
async def read_batch_year_phases(
    year: int,
    reference_year: int | None = Query(default=None, ge=2000, le=2100),
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await batch_service.list_year_phases(year, reference_year)


@router.get("/batches/years/{year}/phases/{phase}/candidates", response_model=list[CandidateOut], summary="List unassigned candidates available for a phase")
async def read_phase_candidates(
    year: int,
    phase: str,
    q: str | None = Query(default=None),
    tech_stack: str | None = Query(default=None),
    college: str | None = Query(default=None),
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
) -> list[dict]:
    return await batch_service.list_phase_candidates(year, phase, q=q, tech_stack=tech_stack, college=college)


@router.post("/batches/years/{year}/phase-cards", response_model=YearPhaseOut, summary="Create a year phase card")
async def create_year_phase_card(
    year: int,
    payload: YearPhaseCardCreate,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await batch_service.create_year_phase_card(year, payload)


@router.get("/batches/years/{year}/phase-cards/{phase}", response_model=YearPhaseOut, summary="View a year phase card with its nested batches")
async def read_year_phase_card(
    year: int,
    phase: str,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await batch_service.get_year_phase_card(year, phase)


@router.post("/batches/years/{year}/phases/{phase}/candidates/import-emails", response_model=CandidateEmailsImportResult, summary="Add candidates to a phase using comma-separated emails")
async def import_phase_candidates(
    year: int,
    phase: str,
    payload: CandidateEmailsImportRequest,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await batch_service.import_phase_candidates_by_email(year, phase, payload)


@router.get("/batches/assignable-owners", response_model=list[UserOut], summary="List batch owners assignable to batches")
async def read_assignable_batch_owners(
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
) -> list[dict]:
    return await batch_service.list_assignable_batch_owners(user.id)


@router.post("/batches/years/{year}/phases/{phase}/batches", response_model=BatchOut, summary="Create a batch card within a phase and assign owner")
async def create_phase_batch(
    year: int,
    phase: str,
    payload: PhaseBatchCreate,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
) -> dict:
    return await batch_service.create_phase_batch(year, phase, payload)


@router.patch("/batches/{batch_id}/owner", response_model=BatchOut, summary="Assign or reassign batch owner")
async def update_batch_owner(
    batch_id: str,
    payload: BatchOwnerAssignRequest,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
) -> dict:
    return await batch_service.assign_batch_owner(batch_id, payload)


@router.post("/batches/{batch_id}/candidates/assign-emails", response_model=CandidateEmailsImportResult, summary="Assign comma-separated candidate emails to a created batch")
async def assign_batch_candidates_by_email(
    batch_id: str,
    payload: CandidateEmailsImportRequest,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
):
    return await batch_service.assign_candidates_to_batch_by_email(batch_id, payload)


@router.get(
    "/batches/{batch_id}/candidates/{candidate_id}/timeline",
    response_model=list[TimelineEventOut],
    summary="View candidate timeline for a specific training batch",
)
async def read_batch_candidate_timeline(
    batch_id: str,
    candidate_id: str,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
) -> list[dict]:
    return await batch_service.get_batch_candidate_timeline(batch_id, candidate_id)


@router.post(
    "/candidate-master-records",
    response_model=CandidateOut,
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
    summary="Create candidate master record",
)
async def create_candidate(
    payload: CandidateCreate,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
) -> dict:
    return await batch_service.create_candidate(payload)


@router.get("/dropout-resignation-requests", response_model=list[ChangeRequestOut], summary="View dropout and resignation requests")
async def read_change_requests(
    status: RequestStatus | None = Query(default=None),
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
) -> list[dict]:
    return await request_service.list_change_requests(status)


@router.post(
    "/configuration/rule-change-requests",
    response_model=ChangeRequestOut,
    summary="Send configuration rule change request to Program Manager",
)
async def create_rule_change_request(
    payload: RuleChangeRequestCreate,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
) -> dict:
    return await request_service.create_rule_change_request(user.id, payload)


@router.patch("/dropout-resignation-requests/{request_id}/review", response_model=ChangeRequestOut, summary="Approve or reject dropout/resignation request")
async def review_change_request(
    request_id: str,
    payload: ChangeRequestReview,
    user: CurrentUser = Depends(require_roles(Role.LND_MANAGER)),
) -> dict:
    return await request_service.review_change_request(request_id, user.id, payload)
