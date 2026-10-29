from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, File, UploadFile, status

from .users import get_database, require_roles
from ...exceptions.http_exceptions import bad_request_exception, forbidden_exception, not_found_exception
from ...models.candidate import CandidateBulkCreateRequest, CandidateCreate, CandidateOut, CandidateTimelineEvent, CandidateUpdate
from ...services.user_service import serialize_document
from ...utils.excel_parser import parse_excel_file

router = APIRouter(prefix="/candidates", tags=["Candidates"])


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as exc:
        raise bad_request_exception("Invalid identifier") from exc


async def _enforce_candidate_access(candidate: dict, current_user: dict) -> None:
    if current_user["role"] in {"admin", "program_manager"}:
        return
    batch_id = candidate.get("batch_id")
    if not batch_id:
        raise forbidden_exception("Candidate is not assigned to your batch")
    batch = await get_database().batches.find_one({"_id": _oid(batch_id)})
    if not batch or batch.get("owner_id") != current_user["id"]:
        raise forbidden_exception("Candidate is outside your assigned batches")


@router.post("", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    payload: CandidateCreate,
    current_user: dict = Depends(require_roles("admin", "batch_owner")),
) -> CandidateOut:
    db = get_database()
    if current_user["role"] == "batch_owner" and payload.batch_id:
        batch = await db.batches.find_one({"_id": _oid(payload.batch_id)})
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


@router.post("/bulk-add", response_model=list[CandidateOut], status_code=status.HTTP_201_CREATED)
async def bulk_add_candidates(
    year: int,
    phase: str,
    batch_id: str | None,
    payload: CandidateBulkCreateRequest,
    current_user: dict = Depends(require_roles("admin", "batch_owner")),
) -> list[CandidateOut]:
    db = get_database()
    if current_user["role"] == "batch_owner" and batch_id:
        batch = await db.batches.find_one({"_id": _oid(batch_id)})
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


@router.get("", response_model=list[CandidateOut])
async def list_candidates(
    year: int | None = None,
    batch_id: str | None = None,
    current_user: dict = Depends(require_roles("admin", "batch_owner", "program_manager")),
) -> list[CandidateOut]:
    db = get_database()
    query = {}
    if year is not None:
        query["year"] = year
    if batch_id:
        query["batch_id"] = batch_id
    if current_user["role"] == "batch_owner":
        owned_batches = await db.batches.find({"owner_id": current_user["id"]}).to_list(length=1000)
        query["batch_id"] = {"$in": [str(batch["_id"]) for batch in owned_batches]}

    candidates = await db.candidates.find(query).sort([("year", -1), ("name", 1)]).to_list(length=10000)
    return [CandidateOut(**serialize_document(candidate)) for candidate in candidates]


@router.patch("/{candidate_id}", response_model=CandidateOut)
async def update_candidate(
    candidate_id: str,
    payload: CandidateUpdate,
    current_user: dict = Depends(require_roles("admin", "batch_owner")),
) -> CandidateOut:
    db = get_database()
    candidate = await db.candidates.find_one({"_id": _oid(candidate_id)})
    if not candidate:
        raise not_found_exception("Candidate not found")

    await _enforce_candidate_access(candidate, current_user)
    update_data = {key: value for key, value in payload.model_dump().items() if value is not None}
    if not update_data:
        raise bad_request_exception("No update fields provided")
    update_data["updated_at"] = datetime.now(timezone.utc)
    await db.candidates.update_one({"_id": candidate["_id"]}, {"$set": update_data})
    updated = await db.candidates.find_one({"_id": candidate["_id"]})
    return CandidateOut(**serialize_document(updated))


@router.get("/{candidate_id}/timeline", response_model=list[CandidateTimelineEvent])
async def get_candidate_timeline(
    candidate_id: str,
    current_user: dict = Depends(require_roles("admin", "batch_owner", "program_manager")),
) -> list[CandidateTimelineEvent]:
    db = get_database()
    candidate = await db.candidates.find_one({"_id": _oid(candidate_id)})
    if not candidate:
        raise not_found_exception("Candidate not found")
    await _enforce_candidate_access(candidate, current_user)

    events = await db.audit_logs.find({"entity_type": "candidate", "entity_id": candidate_id}).sort("created_at", -1).to_list(length=500)
    return [CandidateTimelineEvent(**serialize_document(event)) for event in events]


@router.post("/knowledge-check/upload", response_model=list[CandidateOut])
async def upload_knowledge_check_candidates(
    year: int,
    current_user: dict = Depends(require_roles("admin")),
    file: UploadFile = File(...),
) -> list[CandidateOut]:
    records = parse_excel_file(await file.read(), ["name", "email"])
    db = get_database()
    now = datetime.now(timezone.utc)
    candidates: list[CandidateOut] = []
    for row in records:
        await db.candidates.update_one(
            {"year": year, "email": row["email"].lower()},
            {
                "$set": {
                    "year": year,
                    "name": row["name"],
                    "email": row["email"].lower(),
                    "college": row.get("college"),
                    "percentage": row.get("percentage"),
                    "phase": "post_onboarding",
                    "batch_id": None,
                    "status": "post_onboarding",
                    "offer_accepted": False,
                    "source": "knowledge_check",
                    "created_at": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        candidate = await db.candidates.find_one({"year": year, "email": row["email"].lower()})
        candidates.append(CandidateOut(**serialize_document(candidate)))
    return candidates
