from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, UploadFile, status

from .deps import enforce_batch_owner_access, enforce_candidate_access, get_database, require_roles, to_object_id
from ...exceptions.http_exceptions import bad_request_exception, forbidden_exception, not_found_exception
from ...models.batch import BatchAssignCandidatesRequest, BatchOut, BatchUpdate
from ...models.candidate import CandidateBulkCreateRequest, CandidateCreate, CandidateOut, CandidateTimelineEvent, CandidateUpdate
from ...models.exam import ExamCreate, ExamOut, ExamUpdate
from ...services.batch_service import BatchService
from ...services.exam_service import ExamService
from ...services.user_service import serialize_document
from ...utils.excel_parser import parse_excel_file

router = APIRouter(prefix="/batch-owner", tags=["Batch Owner"])


def get_batch_service() -> BatchService:
    return BatchService(get_database())


def get_exam_service() -> ExamService:
    return ExamService(get_database())


@router.get("/me")
async def read_me(current_user: dict = Depends(require_roles("batch_owner"))) -> dict:
    return current_user


@router.get("/dashboard")
async def get_dashboard(current_user: dict = Depends(require_roles("batch_owner"))) -> dict:
    db = get_database()
    owned_batches = await db.batches.find({"owner_id": current_user["id"]}).to_list(length=1000)
    batch_ids = [str(batch["_id"]) for batch in owned_batches]
    return {
        "assigned_batches": len(owned_batches),
        "candidate_count": await db.candidates.count_documents({"batch_id": {"$in": batch_ids}}),
        "pending_dropouts": await db.dropouts.count_documents({"requested_by": current_user["id"], "status": "pending_admin_review", "is_active": True}),
        "exam_records": await db.exams.count_documents({"batch_id": {"$in": batch_ids}}),
    }


@router.get("/batches", response_model=list[BatchOut])
async def list_batches(
    current_user: dict = Depends(require_roles("batch_owner")),
    service: BatchService = Depends(get_batch_service),
) -> list[BatchOut]:
    return await service.list_batches(current_user)


@router.patch("/batches/{batch_id}", response_model=BatchOut)
async def update_batch(
    batch_id: str,
    payload: BatchUpdate,
    current_user: dict = Depends(require_roles("batch_owner")),
    service: BatchService = Depends(get_batch_service),
) -> BatchOut:
    return await service.update_batch(batch_id, payload, current_user)


@router.post("/batches/{batch_id}/assign-candidates")
async def assign_candidates(
    batch_id: str,
    payload: BatchAssignCandidatesRequest,
    current_user: dict = Depends(require_roles("batch_owner")),
    service: BatchService = Depends(get_batch_service),
) -> dict:
    return await service.assign_candidates(batch_id, payload.candidate_ids, current_user)


@router.get("/batches/{batch_id}/export")
async def export_batch_candidates(
    batch_id: str,
    current_user: dict = Depends(require_roles("batch_owner")),
    service: BatchService = Depends(get_batch_service),
) -> list[dict]:
    return await service.export_batch_candidates(batch_id, current_user)


@router.get("/batches/{batch_id}/available-candidates", response_model=list[CandidateOut])
async def list_available_candidates_for_batch(
    batch_id: str,
    current_user: dict = Depends(require_roles("batch_owner")),
) -> list[CandidateOut]:
    db = get_database()
    batch = await db.batches.find_one({"_id": to_object_id(batch_id)})
    if not batch or batch.get("owner_id") != current_user["id"]:
        raise forbidden_exception("You can only view candidates for your own batches")
    candidates = await db.candidates.find(
        {
            "year": batch["year"],
            "phase": batch["phase"],
            "$or": [{"batch_id": None}, {"batch_id": str(batch["_id"])}],
        }
    ).sort("name", 1).to_list(length=5000)
    return [CandidateOut(**serialize_document(candidate)) for candidate in candidates]


@router.post("/candidates", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    payload: CandidateCreate,
    current_user: dict = Depends(require_roles("batch_owner")),
) -> CandidateOut:
    db = get_database()
    if payload.batch_id:
        batch = await db.batches.find_one({"_id": to_object_id(payload.batch_id)})
        if not batch or batch.get("owner_id") != current_user["id"]:
            raise forbidden_exception("You can only create candidates in your own batches")
    now = datetime.now(timezone.utc)
    result = await db.candidates.insert_one(
        {
            **payload.model_dump(),
            "status": "pre_onboarding" if payload.phase == "pre_onboarding" else "master_imported",
            "offer_accepted": False,
            "source": "manual",
            "created_at": now,
            "updated_at": now,
        }
    )
    candidate = await db.candidates.find_one({"_id": result.inserted_id})
    return CandidateOut(**serialize_document(candidate))


@router.post("/candidates/bulk-add", response_model=list[CandidateOut], status_code=status.HTTP_201_CREATED)
async def bulk_add_candidates(
    year: int,
    phase: str,
    batch_id: str | None,
    payload: CandidateBulkCreateRequest,
    current_user: dict = Depends(require_roles("batch_owner")),
) -> list[CandidateOut]:
    db = get_database()
    if batch_id:
        batch = await db.batches.find_one({"_id": to_object_id(batch_id)})
        if not batch or batch.get("owner_id") != current_user["id"]:
            raise forbidden_exception("You can only add candidates to your own batches")
    now = datetime.now(timezone.utc)
    created: list[CandidateOut] = []
    for email in payload.emails:
        document = {
            "year": year,
            "name": email.split("@")[0],
            "email": email.lower(),
            "college": None,
            "percentage": None,
            "phase": phase,
            "batch_id": batch_id,
            "status": phase,
            "offer_accepted": False,
            "source": "manual_email_list",
            "created_at": now,
            "updated_at": now,
        }
        await db.candidates.update_one({"year": year, "email": email.lower()}, {"$set": document}, upsert=True)
        candidate = await db.candidates.find_one({"year": year, "email": email.lower()})
        created.append(CandidateOut(**serialize_document(candidate)))
    return created


@router.get("/candidates", response_model=list[CandidateOut])
async def list_candidates(
    year: int | None = None,
    current_user: dict = Depends(require_roles("batch_owner")),
) -> list[CandidateOut]:
    db = get_database()
    owned_batches = await db.batches.find({"owner_id": current_user["id"]}).to_list(length=1000)
    query = {"batch_id": {"$in": [str(batch["_id"]) for batch in owned_batches]}}
    if year is not None:
        query["year"] = year
    candidates = await db.candidates.find(query).sort([("year", -1), ("name", 1)]).to_list(length=10000)
    return [CandidateOut(**serialize_document(candidate)) for candidate in candidates]


@router.patch("/candidates/{candidate_id}", response_model=CandidateOut)
async def update_candidate(
    candidate_id: str,
    payload: CandidateUpdate,
    current_user: dict = Depends(require_roles("batch_owner")),
) -> CandidateOut:
    db = get_database()
    candidate = await db.candidates.find_one({"_id": to_object_id(candidate_id)})
    if not candidate:
        raise not_found_exception("Candidate not found")
    await enforce_candidate_access(candidate, current_user)
    update_data = {key: value for key, value in payload.model_dump().items() if value is not None}
    if not update_data:
        raise bad_request_exception("No update fields provided")
    update_data["updated_at"] = datetime.now(timezone.utc)
    await db.candidates.update_one({"_id": candidate["_id"]}, {"$set": update_data})
    updated = await db.candidates.find_one({"_id": candidate["_id"]})
    return CandidateOut(**serialize_document(updated))


@router.get("/candidates/{candidate_id}/timeline", response_model=list[CandidateTimelineEvent])
async def get_candidate_timeline(
    candidate_id: str,
    current_user: dict = Depends(require_roles("batch_owner")),
) -> list[CandidateTimelineEvent]:
    db = get_database()
    candidate = await db.candidates.find_one({"_id": to_object_id(candidate_id)})
    if not candidate:
        raise not_found_exception("Candidate not found")
    await enforce_candidate_access(candidate, current_user)
    events = await db.audit_logs.find({"entity_type": "candidate", "entity_id": candidate_id}).sort("created_at", -1).to_list(length=500)
    return [CandidateTimelineEvent(**serialize_document(event)) for event in events]


@router.post("/exams", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
async def create_exam(
    payload: ExamCreate,
    current_user: dict = Depends(require_roles("batch_owner")),
    service: ExamService = Depends(get_exam_service),
) -> ExamOut:
    return await service.create_exam(payload, current_user)


@router.get("/exams", response_model=list[ExamOut])
async def list_exams(
    exam_type: str | None = None,
    current_user: dict = Depends(require_roles("batch_owner")),
    service: ExamService = Depends(get_exam_service),
) -> list[ExamOut]:
    return await service.list_exams(current_user, exam_type)


@router.patch("/exams/{exam_id}", response_model=ExamOut)
async def update_exam(
    exam_id: str,
    payload: ExamUpdate,
    current_user: dict = Depends(require_roles("batch_owner")),
    service: ExamService = Depends(get_exam_service),
) -> ExamOut:
    return await service.update_exam(exam_id, payload, current_user)


@router.post("/exams/baseline/upload", response_model=list[ExamOut])
async def upload_baseline_scores(
    batch_id: str | None = None,
    current_user: dict = Depends(require_roles("batch_owner")),
    file: UploadFile = File(...),
) -> list[ExamOut]:
    await enforce_batch_owner_access(batch_id, current_user)
    records = parse_excel_file(await file.read(), ["candidate_email", "score", "attended", "passed"])
    db = get_database()
    service = get_exam_service()
    created: list[ExamOut] = []
    for row in records:
        candidate = await db.candidates.find_one({"email": row["candidate_email"].lower()})
        if not candidate:
            raise not_found_exception(f"Candidate not found for email {row['candidate_email']}")
        created.append(
            await service.create_exam(
                ExamCreate(
                    candidate_id=str(candidate["_id"]),
                    exam_type="baseline",
                    coding_name=None,
                    score=float(row["score"]) if row["score"] is not None else None,
                    attended=bool(row["attended"]),
                    passed=bool(row["passed"]),
                    attempt_number=1,
                    status="passed" if bool(row["passed"]) else ("not_attended" if not bool(row["attended"]) else "failed"),
                    batch_id=batch_id or candidate.get("batch_id"),
                ),
                current_user,
            )
        )
    return created


@router.post("/exams/knowledge-check/upload", response_model=list[ExamOut])
async def upload_knowledge_check_scores(
    coding_name: str,
    batch_id: str | None = None,
    current_user: dict = Depends(require_roles("batch_owner")),
    file: UploadFile = File(...),
) -> list[ExamOut]:
    await enforce_batch_owner_access(batch_id, current_user)
    records = parse_excel_file(await file.read(), ["candidate_email", "score", "attended", "passed", "attempt_number"])
    db = get_database()
    service = get_exam_service()
    created: list[ExamOut] = []
    for row in records:
        candidate = await db.candidates.find_one({"email": row["candidate_email"].lower()})
        if not candidate:
            raise not_found_exception(f"Candidate not found for email {row['candidate_email']}")
        created.append(
            await service.create_exam(
                ExamCreate(
                    candidate_id=str(candidate["_id"]),
                    exam_type="knowledge_check",
                    coding_name=coding_name,
                    score=float(row["score"]) if row["score"] is not None else None,
                    attended=bool(row["attended"]),
                    passed=bool(row["passed"]),
                    attempt_number=int(row["attempt_number"]),
                    status="passed" if bool(row["passed"]) else ("not_attended" if not bool(row["attended"]) else "failed"),
                    batch_id=batch_id or candidate.get("batch_id"),
                ),
                current_user,
            )
        )
    return created


@router.post("/dropouts/{candidate_id}/mark")
async def mark_dropout(
    candidate_id: str,
    reason: str,
    current_user: dict = Depends(require_roles("batch_owner")),
) -> dict:
    db = get_database()
    candidate = await db.candidates.find_one({"_id": to_object_id(candidate_id)})
    if not candidate:
        raise not_found_exception("Candidate not found")
    await enforce_candidate_access(candidate, current_user)
    now = datetime.now(timezone.utc)
    await db.dropouts.update_one(
        {"candidate_id": candidate_id, "is_active": True},
        {"$set": {
            "candidate_id": candidate_id,
            "candidate_year": candidate["year"],
            "reason": reason,
            "requested_by": current_user["id"],
            "finalized_by": None,
            "is_active": True,
            "status": "pending_admin_review",
            "created_at": now,
            "updated_at": now,
        }},
        upsert=True,
    )
    await db.candidates.update_one({"_id": candidate["_id"]}, {"$set": {"status": "dropout_pending", "updated_at": now}})
    return {"message": "Dropout marked and sent for admin review"}
