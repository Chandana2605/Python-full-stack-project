from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, UploadFile, status

from .deps import get_database, get_user_service, require_roles, to_object_id
from ...exceptions.http_exceptions import bad_request_exception, not_found_exception
from ...models.approval import ApprovalOut, ApprovalRequestCreate, RuleChangeRequestCreate
from ...models.batch import BatchAssignCandidatesRequest, BatchCreate, BatchOut, BatchUpdate
from ...models.candidate import (
    CandidateBulkCreateRequest,
    CandidateCreate,
    CandidateEmailImportRequest,
    CandidateOut,
    CandidateTimelineEvent,
    CandidateUpdate,
)
from ...models.exam import ExamCreate, ExamOut
from ...models.user import (
    EmailConnectionTestRequest,
    EmailConnectionTestResponse,
    ResendInvitationRequest,
    UserCreate,
    UserOut,
    UserProvisionResponse,
    UserUpdate,
)
from ...services.approval_service import ApprovalService
from ...services.batch_service import BatchService
from ...services.exam_service import ExamService
from ...services.user_service import serialize_document
from ...utils.excel_parser import parse_excel_file

router = APIRouter(prefix="/admin", tags=["Admin"])


def get_batch_service() -> BatchService:
    return BatchService(get_database())


def get_exam_service() -> ExamService:
    return ExamService(get_database())


def get_approval_service() -> ApprovalService:
    return ApprovalService(get_database())


def _parse_csv_emails(emails_csv: str) -> list[str]:
    emails = [item.strip().lower() for item in emails_csv.split(",") if item.strip()]
    if not emails:
        raise bad_request_exception("At least one email is required")
    invalid = [email for email in emails if "@" not in email]
    if invalid:
        raise bad_request_exception(f"Invalid emails: {', '.join(invalid)}")
    return list(dict.fromkeys(emails))


async def _upsert_candidate_for_knowledge_check(row: dict, year: int, batch_id: str | None) -> dict:
    db = get_database()
    now = datetime.now(timezone.utc)
    email = row["candidate_email"].lower()
    document = {
        "year": year,
        "name": row["name"],
        "email": email,
        "college": row.get("college"),
        "percentage": row.get("percentage"),
        "phase": "post_onboarding",
        "batch_id": batch_id,
        "status": "post_onboarding",
        "offer_accepted": False,
        "source": "knowledge_check",
        "created_at": now,
        "updated_at": now,
    }
    await db.candidates.update_one({"year": year, "email": email}, {"$set": document}, upsert=True)
    candidate = await db.candidates.find_one({"year": year, "email": email})
    await db.audit_logs.insert_one(
        {
            "entity_type": "candidate",
            "entity_id": str(candidate["_id"]),
            "action": "knowledge_check_candidate_upserted",
            "message": "Candidate created or updated from knowledge check upload",
            "created_by": None,
            "created_at": now,
        }
    )
    return candidate


@router.get("/me")
async def read_me(current_user: dict = Depends(require_roles("admin"))) -> dict:
    return current_user


@router.get("/dashboard")
async def get_dashboard(_: dict = Depends(require_roles("admin"))) -> dict:
    db = get_database()
    years = sorted(await db.candidates.distinct("year"), reverse=True)
    active_year = years[0] if years else datetime.now(timezone.utc).year
    return {
        "active_year": active_year,
        "users_count": await db.users.count_documents({"is_active": True}),
        "pending_rule_changes": await db.approvals.count_documents({"status": "pending"}),
        "pending_dropouts": await db.dropouts.count_documents({"status": "pending_admin_review", "is_active": True}),
        "active_batches": await db.batches.count_documents({"year": active_year, "is_active": True}),
        "completed_batches": await db.batches.count_documents({"year": active_year - 1, "is_active": False}),
    }


@router.get("/years")
async def list_year_cards(_: dict = Depends(require_roles("admin"))) -> list[dict]:
    db = get_database()
    years = sorted(await db.candidates.distinct("year"), reverse=True)
    current_year = datetime.now(timezone.utc).year
    results = []
    for year in years:
        if year == current_year:
            status = "active"
        elif year == current_year - 1:
            status = "completed"
        else:
            status = "archive"
        results.append(
            {
                "year": year,
                "status": status,
                "candidate_count": await db.candidates.count_documents({"year": year}),
                "batch_count": await db.batches.count_documents({"year": year}),
            }
        )
    return results


@router.get("/archives/{year}")
async def get_year_archive(year: int, _: dict = Depends(require_roles("admin"))) -> dict:
    db = get_database()
    return {
        "year": year,
        "candidates": [serialize_document(item) for item in await db.candidates.find({"year": year}).sort("name", 1).to_list(length=10000)],
        "batches": [serialize_document(item) for item in await db.batches.find({"year": year}).sort("name", 1).to_list(length=1000)],
        "dropouts": [serialize_document(item) for item in await db.dropouts.find({"candidate_year": year}).sort("updated_at", -1).to_list(length=1000)],
    }


@router.post("/users", response_model=UserProvisionResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user: dict = Depends(require_roles("admin")),
    service=Depends(get_user_service),
) -> UserProvisionResponse:
    user = await service.create_user_record(payload, current_user["id"])
    return await service.send_invitation_for_user(
        user_id=user.id,
        temporary_password=payload.temporary_password,
        triggered_by=current_user["id"],
        action="user_created",
    )


@router.get("/users", response_model=list[UserOut])
async def list_users(
    _: dict = Depends(require_roles("admin")),
    service=Depends(get_user_service),
) -> list[UserOut]:
    return await service.list_users()


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    _: dict = Depends(require_roles("admin")),
    service=Depends(get_user_service),
) -> UserOut:
    return await service.update_user(user_id, payload)


@router.post("/users/{user_id}/resend-invitation", response_model=UserProvisionResponse)
async def resend_user_invitation(
    user_id: str,
    payload: ResendInvitationRequest,
    current_user: dict = Depends(require_roles("admin")),
    service=Depends(get_user_service),
) -> UserProvisionResponse:
    return await service.resend_invitation(user_id, payload.temporary_password, current_user["id"])


@router.post("/email/test", response_model=EmailConnectionTestResponse)
async def test_email_trigger(
    payload: EmailConnectionTestRequest,
    current_user: dict = Depends(require_roles("admin")),
    service=Depends(get_user_service),
) -> EmailConnectionTestResponse:
    result = await service.test_email_connection(payload.recipient_email, current_user["id"])
    return EmailConnectionTestResponse(**result)


@router.get("/roles")
async def list_roles(_: dict = Depends(require_roles("admin"))) -> list[dict]:
    roles = await get_database().roles.find().sort("name", 1).to_list(length=50)
    return [serialize_document(role) for role in roles]


@router.post("/master-database/upload", response_model=list[CandidateOut], status_code=status.HTTP_201_CREATED)
async def upload_master_database(
    year: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles("admin")),
) -> list[CandidateOut]:
    records = parse_excel_file(await file.read(), ["name", "college", "email", "percentage"])
    db = get_database()
    now = datetime.now(timezone.utc)
    created_candidates: list[CandidateOut] = []
    for row in records:
        email = (row.get("email") or "").strip().lower()
        if not email:
            raise bad_request_exception("Candidate email is required in master upload")
        document = {
            "year": year,
            "name": row.get("name"),
            "college": row.get("college"),
            "email": email,
            "percentage": row.get("percentage"),
            "phase": None,
            "batch_id": None,
            "status": "master_imported",
            "offer_accepted": False,
            "source": "master_database",
            "created_at": now,
            "updated_at": now,
        }
        await db.candidates.update_one({"year": year, "email": email}, {"$set": document}, upsert=True)
        candidate = await db.candidates.find_one({"year": year, "email": email})
        created_candidates.append(CandidateOut(**serialize_document(candidate)))
        await db.audit_logs.insert_one(
            {
                "entity_type": "candidate",
                "entity_id": str(candidate["_id"]),
                "action": "master_import",
                "message": f"Candidate loaded into master database for year {year}",
                "created_by": current_user["id"],
                "created_at": now,
            }
        )
    return created_candidates


@router.post("/batches", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: BatchCreate,
    current_user: dict = Depends(require_roles("admin")),
    service: BatchService = Depends(get_batch_service),
) -> BatchOut:
    return await service.create_batch(payload, current_user["id"])


@router.get("/batches", response_model=list[BatchOut])
async def list_batches(
    current_user: dict = Depends(require_roles("admin")),
    service: BatchService = Depends(get_batch_service),
) -> list[BatchOut]:
    return await service.list_batches(current_user)


@router.patch("/batches/{batch_id}", response_model=BatchOut)
async def update_batch(
    batch_id: str,
    payload: BatchUpdate,
    current_user: dict = Depends(require_roles("admin")),
    service: BatchService = Depends(get_batch_service),
) -> BatchOut:
    return await service.update_batch(batch_id, payload, current_user)


@router.post("/batches/{batch_id}/assign-candidates")
async def assign_candidates(
    batch_id: str,
    payload: BatchAssignCandidatesRequest,
    current_user: dict = Depends(require_roles("admin")),
    service: BatchService = Depends(get_batch_service),
) -> dict:
    return await service.assign_candidates(batch_id, payload.candidate_ids, current_user)


@router.get("/batches/{batch_id}/export")
async def export_batch_candidates(
    batch_id: str,
    current_user: dict = Depends(require_roles("admin")),
    service: BatchService = Depends(get_batch_service),
) -> list[dict]:
    return await service.export_batch_candidates(batch_id, current_user)


@router.post("/candidates", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    payload: CandidateCreate,
    _: dict = Depends(require_roles("admin")),
) -> CandidateOut:
    db = get_database()
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
    _: dict = Depends(require_roles("admin")),
) -> list[CandidateOut]:
    db = get_database()
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


@router.post("/phases/pre-onboarding/candidates/import", response_model=list[CandidateOut], status_code=status.HTTP_201_CREATED)
async def import_pre_onboarding_candidates(
    year: int,
    payload: CandidateEmailImportRequest,
    batch_id: str | None = None,
    _: dict = Depends(require_roles("admin")),
) -> list[CandidateOut]:
    db = get_database()
    now = datetime.now(timezone.utc)
    created: list[CandidateOut] = []
    for email in _parse_csv_emails(payload.emails_csv):
        document = {
            "year": year,
            "name": email.split("@")[0],
            "email": email,
            "college": None,
            "percentage": None,
            "phase": "pre_onboarding",
            "batch_id": batch_id,
            "status": "pre_onboarding",
            "offer_accepted": False,
            "source": "manual_email_list",
            "created_at": now,
            "updated_at": now,
        }
        await db.candidates.update_one({"year": year, "email": email}, {"$set": document}, upsert=True)
        candidate = await db.candidates.find_one({"year": year, "email": email})
        created.append(CandidateOut(**serialize_document(candidate)))
    return created


@router.get("/candidates", response_model=list[CandidateOut])
async def list_candidates(
    year: int | None = None,
    batch_id: str | None = None,
    _: dict = Depends(require_roles("admin")),
) -> list[CandidateOut]:
    db = get_database()
    query = {}
    if year is not None:
        query["year"] = year
    if batch_id:
        query["batch_id"] = batch_id
    candidates = await db.candidates.find(query).sort([("year", -1), ("name", 1)]).to_list(length=10000)
    return [CandidateOut(**serialize_document(candidate)) for candidate in candidates]


@router.patch("/candidates/{candidate_id}", response_model=CandidateOut)
async def update_candidate(
    candidate_id: str,
    payload: CandidateUpdate,
    _: dict = Depends(require_roles("admin")),
) -> CandidateOut:
    db = get_database()
    candidate = await db.candidates.find_one({"_id": to_object_id(candidate_id)})
    if not candidate:
        raise not_found_exception("Candidate not found")
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
    _: dict = Depends(require_roles("admin")),
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
    current_user: dict = Depends(require_roles("admin")),
    service: ExamService = Depends(get_exam_service),
) -> list[ExamOut]:
    return await service.list_exams(current_user, exam_type)


@router.post("/exams/baseline/upload", response_model=list[ExamOut])
async def upload_baseline_scores(
    batch_id: str | None = None,
    current_user: dict = Depends(require_roles("admin")),
    file: UploadFile = File(...),
) -> list[ExamOut]:
    records = parse_excel_file(await file.read(), ["candidate_email", "score", "attended", "passed"])
    db = get_database()
    service = get_exam_service()
    created: list[ExamOut] = []
    for row in records:
        candidate = await db.candidates.find_one({"email": row["candidate_email"].lower()})
        if not candidate:
            raise not_found_exception(f"Candidate not found for email {row['candidate_email']}")
        created.append(
            await service.create_or_update_exam(
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
    year: int,
    batch_id: str | None = None,
    current_user: dict = Depends(require_roles("admin")),
    file: UploadFile = File(...),
) -> list[ExamOut]:
    records = parse_excel_file(
        await file.read(),
        [
            "name",
            "college",
            "candidate_email",
            "percentage",
            "coding_name",
            "score",
            "attended",
            "passed",
            "attempt_number",
        ],
    )
    service = get_exam_service()
    created: list[ExamOut] = []
    for row in records:
        candidate = await _upsert_candidate_for_knowledge_check(row, year, batch_id)
        created.append(
            await service.create_or_update_exam(
                ExamCreate(
                    candidate_id=str(candidate["_id"]),
                    exam_type="knowledge_check",
                    coding_name=row["coding_name"],
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


@router.post("/approvals", response_model=ApprovalOut, status_code=status.HTTP_201_CREATED)
async def create_rule_change_request(
    payload: ApprovalRequestCreate,
    current_user: dict = Depends(require_roles("admin")),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalOut:
    return await service.create_request(payload, current_user["id"])


@router.post("/approvals/rule-change", response_model=ApprovalOut, status_code=status.HTTP_201_CREATED)
async def create_structured_rule_change_request(
    payload: RuleChangeRequestCreate,
    current_user: dict = Depends(require_roles("admin")),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalOut:
    request = ApprovalRequestCreate(
        target_type="rule_configuration",
        target_id=payload.batch_id,
        title=f"Rule change for {payload.exam_name}",
        requested_change=payload.reason,
        proposed_value=(
            f"phase={payload.phase}; exam_name={payload.exam_name}; "
            f"current_pass_percentage={payload.current_pass_percentage}; "
            f"requested_pass_percentage={payload.requested_pass_percentage}"
        ),
    )
    return await service.create_request(request, current_user["id"])


@router.get("/approvals", response_model=list[ApprovalOut])
async def list_rule_change_requests(
    status: str | None = None,
    _: dict = Depends(require_roles("admin")),
    service: ApprovalService = Depends(get_approval_service),
) -> list[ApprovalOut]:
    return await service.list_requests(status)


@router.get("/notifications")
async def get_notifications(_: dict = Depends(require_roles("admin"))) -> dict:
    db = get_database()
    return {
        "pending_dropouts": [serialize_document(item) for item in await db.dropouts.find({"status": "pending_admin_review", "is_active": True}).sort("updated_at", -1).to_list(length=500)],
        "pending_rule_changes": [serialize_document(item) for item in await db.approvals.find({"status": "pending"}).sort("created_at", -1).to_list(length=500)],
    }


@router.post("/dropouts/{candidate_id}/mark")
async def mark_dropout(
    candidate_id: str,
    reason: str,
    current_user: dict = Depends(require_roles("admin")),
) -> dict:
    db = get_database()
    candidate = await db.candidates.find_one({"_id": to_object_id(candidate_id)})
    if not candidate:
        raise not_found_exception("Candidate not found")
    now = datetime.now(timezone.utc)
    await db.dropouts.update_one(
        {"candidate_id": candidate_id, "is_active": True},
        {"$set": {
            "candidate_id": candidate_id,
            "candidate_year": candidate["year"],
            "reason": reason,
            "requested_by": current_user["id"],
            "finalized_by": current_user["id"],
            "is_active": True,
            "status": "finalized",
            "created_at": now,
            "updated_at": now,
        }},
        upsert=True,
    )
    await db.candidates.update_one({"_id": candidate["_id"]}, {"$set": {"status": "dropout_finalized", "updated_at": now}})
    return {"message": "Dropout finalized"}


@router.post("/dropouts/{candidate_id}/revoke")
async def revoke_dropout(
    candidate_id: str,
    _: dict = Depends(require_roles("admin")),
) -> dict:
    db = get_database()
    candidate = await db.candidates.find_one({"_id": to_object_id(candidate_id)})
    if not candidate:
        raise not_found_exception("Candidate not found")
    now = datetime.now(timezone.utc)
    await db.dropouts.update_many({"candidate_id": candidate_id, "is_active": True}, {"$set": {"is_active": False, "updated_at": now}})
    await db.candidates.update_one({"_id": candidate["_id"]}, {"$set": {"status": "post_onboarding", "updated_at": now}})
    return {"message": "Dropout revoked successfully"}


@router.get("/analytics/funnel")
async def get_funnel_metrics(
    year: int | None = None,
    _: dict = Depends(require_roles("admin")),
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
    _: dict = Depends(require_roles("admin")),
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
async def get_year_comparison(_: dict = Depends(require_roles("admin"))) -> list[dict]:
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
