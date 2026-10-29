from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import PlainTextResponse

from app.api.deps import require_roles
from app.core.enums import CandidateStatus, ExamPhase, RequestStatus, Role
from app.schemas.auth import CurrentUser
from app.schemas.batches import (
    BatchDetailsUpdate,
    BatchOut,
    CandidateAssignRequest,
    CandidateEmploymentUpdate,
    CandidateOut,
    ChangeRequestCreate,
    ChangeRequestOut,
    ExamResultOut,
    ExamScoreInput,
    MarksUpdate,
    TimelineEventOut,
)
from app.services import batch_service, exam_service, request_service
from app.services.export_service import candidates_to_csv

router = APIRouter()


@router.get("/assigned-batches", response_model=list[BatchOut], summary="View batches assigned to the owner")
async def my_batches(user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER))) -> list[dict]:
    return await batch_service.list_assigned_batches(user.id)


@router.patch("/assigned-batches/{batch_id}/configuration", response_model=BatchOut, summary="Configure assigned batch details")
async def configure_batch(
    batch_id: str,
    payload: BatchDetailsUpdate,
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> dict:
    return await batch_service.update_batch_details(batch_id, user.id, payload)


@router.post(
    "/assigned-batches/{batch_id}/eligible-candidates",
    response_model=list[CandidateOut],
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
    summary="Assign eligible candidates to a batch",
)
async def assign_candidates(
    batch_id: str,
    payload: CandidateAssignRequest,
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> list[dict]:
    return await batch_service.assign_candidates(batch_id, user.id, payload.candidate_ids)


@router.get(
    "/assigned-batches/{batch_id}/eligible-candidates",
    response_model=list[CandidateOut],
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
    summary="View candidates eligible for the batch phase",
)
async def list_eligible_candidates_for_batch(
    batch_id: str,
    q: str | None = Query(default=None),
    tech_stack: str | None = Query(default=None),
    college: str | None = Query(default=None),
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> list[dict]:
    return await batch_service.list_eligible_candidates_for_batch_phase(batch_id, user.id, q, tech_stack, college)


@router.get(
    "/assigned-batches/{batch_id}/candidates",
    response_model=list[CandidateOut],
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
    summary="Search and filter candidates in an assigned batch",
)
async def list_candidates(
    batch_id: str,
    q: str | None = Query(default=None),
    status: CandidateStatus | None = Query(default=None),
    tech_stack: str | None = Query(default=None),
    college: str | None = Query(default=None),
    eligible_phase: ExamPhase | None = Query(default=None),
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> list[dict]:
    return await batch_service.list_batch_candidates(
        batch_id, user.id, q, status.value if status else None, tech_stack, college, eligible_phase.value if eligible_phase else None
    )


@router.get("/assigned-batches/{batch_id}/candidate-export", response_class=PlainTextResponse, summary="Export assigned batch candidate data as CSV")
async def export_candidates(
    batch_id: str,
    q: str | None = Query(default=None),
    status: CandidateStatus | None = Query(default=None),
    tech_stack: str | None = Query(default=None),
    college: str | None = Query(default=None),
    eligible_phase: ExamPhase | None = Query(default=None),
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> str:
    candidates = await batch_service.list_batch_candidates(
        batch_id, user.id, q, status.value if status else None, tech_stack, college, eligible_phase.value if eligible_phase else None
    )
    return candidates_to_csv(candidates)


@router.get("/candidates/{candidate_id}/timeline", response_model=list[TimelineEventOut], summary="View complete candidate timeline")
async def candidate_timeline(
    candidate_id: str,
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> list[dict]:
    return await batch_service.get_candidate_timeline(candidate_id, user.id, require_owned=True)


@router.patch(
    "/assigned-batches/{batch_id}/candidates/{candidate_id}/manual-marks",
    response_model=CandidateOut,
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
    summary="Manually update candidate marks",
)
async def update_marks(
    batch_id: str,
    candidate_id: str,
    payload: MarksUpdate,
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> dict:
    return await batch_service.update_candidate_marks(batch_id, candidate_id, user.id, payload)


@router.patch(
    "/assigned-batches/{batch_id}/candidates/{candidate_id}/employment-details",
    response_model=CandidateOut,
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
    summary="Update post-onboarding candidate UID and employee email",
)
async def update_employment_details(
    batch_id: str,
    candidate_id: str,
    payload: CandidateEmploymentUpdate,
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> dict:
    return await batch_service.update_candidate_employment_details(batch_id, candidate_id, user.id, payload)


@router.post("/assigned-batches/{batch_id}/exam-results", response_model=ExamResultOut, summary="Record manual pre/post onboarding exam result")
async def record_exam(
    batch_id: str,
    payload: ExamScoreInput,
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> dict:
    return await exam_service.record_exam_score(batch_id, user.id, payload)


@router.post("/assigned-batches/{batch_id}/exam-results/excel-upload", response_model=list[ExamResultOut], summary="Upload exam results from Excel")
async def upload_exams(
    batch_id: str,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> list[dict]:
    return await exam_service.upload_exam_scores(batch_id, user.id, file)


@router.get("/assigned-batches/exam-results/template", response_class=PlainTextResponse, summary="Download sample exam bulk upload template")
async def download_exam_template(
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> str:
    return exam_service.exam_template_csv()


@router.get("/assigned-batches/{batch_id}/exam-results", response_model=list[ExamResultOut], summary="View assigned batch exam results")
async def list_exams(
    batch_id: str,
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> list[dict]:
    return await exam_service.list_exam_results(batch_id, user.id)


@router.post("/assigned-batches/{batch_id}/dropout-resignation-requests", response_model=ChangeRequestOut, summary="Submit dropout or resignation request")
async def submit_change_request(
    batch_id: str,
    payload: ChangeRequestCreate,
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> dict:
    return await request_service.create_change_request(batch_id, user.id, payload)


@router.get("/dropout-resignation-requests", response_model=list[ChangeRequestOut], summary="View submitted dropout or resignation requests")
async def read_my_change_requests(
    status: RequestStatus | None = Query(default=None),
    user: CurrentUser = Depends(require_roles(Role.BATCH_OWNER)),
) -> list[dict]:
    return await request_service.list_owner_change_requests(user.id, status)
