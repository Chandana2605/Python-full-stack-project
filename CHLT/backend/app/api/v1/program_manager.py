from fastapi import APIRouter, Depends

from .deps import get_database, require_roles, to_object_id
from ...exceptions.http_exceptions import not_found_exception
from ...models.approval import ApprovalDecision, ApprovalOut
from ...models.batch import BatchOut
from ...models.candidate import CandidateOut, CandidateTimelineEvent
from ...models.exam import ExamOut
from ...services.approval_service import ApprovalService
from ...services.batch_service import BatchService
from ...services.exam_service import ExamService
from ...services.user_service import serialize_document

router = APIRouter(prefix="/program-manager", tags=["Program Manager"])


def get_batch_service() -> BatchService:
    return BatchService(get_database())


def get_exam_service() -> ExamService:
    return ExamService(get_database())


def get_approval_service() -> ApprovalService:
    return ApprovalService(get_database())


@router.get("/me")
async def read_me(current_user: dict = Depends(require_roles("program_manager"))) -> dict:
    return current_user


@router.get("/dashboard")
async def get_dashboard(_: dict = Depends(require_roles("program_manager"))) -> dict:
    db = get_database()
    years = sorted(await db.candidates.distinct("year"), reverse=True)
    current_year = years[0] if years else None
    return {
        "current_year": current_year,
        "pending_rule_changes": await db.approvals.count_documents({"status": "pending"}),
        "candidate_count": await db.candidates.count_documents({}),
        "batch_count": await db.batches.count_documents({}),
    }


@router.get("/roles")
async def list_roles(_: dict = Depends(require_roles("program_manager"))) -> list[dict]:
    roles = await get_database().roles.find().sort("name", 1).to_list(length=50)
    return [serialize_document(role) for role in roles]


@router.get("/batches", response_model=list[BatchOut])
async def list_batches(
    current_user: dict = Depends(require_roles("program_manager")),
    service: BatchService = Depends(get_batch_service),
) -> list[BatchOut]:
    return await service.list_batches(current_user)


@router.get("/candidates", response_model=list[CandidateOut])
async def list_candidates(
    year: int | None = None,
    batch_id: str | None = None,
    _: dict = Depends(require_roles("program_manager")),
) -> list[CandidateOut]:
    db = get_database()
    query = {}
    if year is not None:
        query["year"] = year
    if batch_id:
        query["batch_id"] = batch_id
    candidates = await db.candidates.find(query).sort([("year", -1), ("name", 1)]).to_list(length=10000)
    return [CandidateOut(**serialize_document(candidate)) for candidate in candidates]


@router.get("/candidates/{candidate_id}/timeline", response_model=list[CandidateTimelineEvent])
async def get_candidate_timeline(
    candidate_id: str,
    _: dict = Depends(require_roles("program_manager")),
) -> list[CandidateTimelineEvent]:
    db = get_database()
    candidate = await db.candidates.find_one({"_id": to_object_id(candidate_id)})
    if not candidate:
        raise not_found_exception("Candidate not found")
    events = await db.audit_logs.find({"entity_type": "candidate", "entity_id": candidate_id}).sort("created_at", -1).to_list(length=500)
    return [CandidateTimelineEvent(**serialize_document(event)) for event in events]


@router.get("/exams", response_model=list[ExamOut])
async def list_exams(
    exam_type: str | None = None,
    current_user: dict = Depends(require_roles("program_manager")),
    service: ExamService = Depends(get_exam_service),
) -> list[ExamOut]:
    return await service.list_exams(current_user, exam_type)


@router.get("/approvals", response_model=list[ApprovalOut])
async def list_rule_change_requests(
    status: str | None = None,
    _: dict = Depends(require_roles("program_manager")),
    service: ApprovalService = Depends(get_approval_service),
) -> list[ApprovalOut]:
    return await service.list_requests(status)


@router.post("/approvals/{approval_id}/decision", response_model=ApprovalOut)
async def decide_rule_change_request(
    approval_id: str,
    payload: ApprovalDecision,
    current_user: dict = Depends(require_roles("program_manager")),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalOut:
    return await service.decide_request(approval_id, payload, current_user["id"])


@router.get("/analytics/funnel")
async def get_funnel_metrics(
    year: int | None = None,
    _: dict = Depends(require_roles("program_manager")),
) -> dict:
    db = get_database()
    query = {"year": year} if year is not None else {}
    return {
        "year": year,
        "total_candidates": await db.candidates.count_documents(query),
        "eligible_for_offer": await db.candidates.count_documents({**query, "status": "eligible_for_offer"}),
        "deployment_ready": await db.candidates.count_documents({**query, "status": "deployment_ready"}),
        "referred_to_hr": await db.candidates.count_documents({**query, "status": "referred_to_hr"}),
        "active_dropouts": await db.dropouts.count_documents({"is_active": True, **({"candidate_year": year} if year is not None else {})}),
    }


@router.get("/analytics/batch-performance")
async def get_batch_performance(
    year: int | None = None,
    _: dict = Depends(require_roles("program_manager")),
) -> list[dict]:
    db = get_database()
    query = {"year": year} if year is not None else {}
    batches = await db.batches.find(query).to_list(length=1000)
    results = []
    for batch in batches:
        batch_id = str(batch["_id"])
        results.append(
            {
                "batch_id": batch_id,
                "batch_name": batch["name"],
                "year": batch["year"],
                "phase": batch["phase"],
                "total_candidates": await db.candidates.count_documents({"batch_id": batch_id}),
                "deployment_ready": await db.candidates.count_documents({"batch_id": batch_id, "status": "deployment_ready"}),
            }
        )
    return results


@router.get("/analytics/year-comparison")
async def get_year_comparison(_: dict = Depends(require_roles("program_manager"))) -> list[dict]:
    db = get_database()
    years = sorted(await db.candidates.distinct("year"))
    comparison = []
    for year in years:
        comparison.append(
            {
                "year": year,
                "total_candidates": await db.candidates.count_documents({"year": year}),
                "eligible_for_offer": await db.candidates.count_documents({"year": year, "status": "eligible_for_offer"}),
                "deployment_ready": await db.candidates.count_documents({"year": year, "status": "deployment_ready"}),
                "completed_batches": await db.batches.count_documents({"year": year, "is_active": False}),
            }
        )
    return comparison


@router.get("/archives/{year}")
async def get_year_archive(year: int, _: dict = Depends(require_roles("program_manager"))) -> dict:
    db = get_database()
    return {
        "year": year,
        "candidates": [serialize_document(item) for item in await db.candidates.find({"year": year}).sort("name", 1).to_list(length=10000)],
        "batches": [serialize_document(item) for item in await db.batches.find({"year": year}).sort("name", 1).to_list(length=1000)],
        "approvals": [serialize_document(item) for item in await db.approvals.find({"target_id": {"$exists": True}}).sort("created_at", -1).to_list(length=1000)],
    }
