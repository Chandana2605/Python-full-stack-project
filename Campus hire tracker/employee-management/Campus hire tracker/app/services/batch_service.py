from datetime import datetime
from typing import Any
import re

from fastapi import HTTPException, status

from app.core.enums import CandidateStatus, ExamPhase, Role, TimelineEventType
from app.db.postgresql import get_database
from app.schemas.batches import (
    BatchOwnerAssignRequest,
    BatchCreate,
    BatchDetailsUpdate,
    CandidateEmailsImportRequest,
    CandidateEmailsImportResult,
    CandidateCreate,
    CandidateEmploymentUpdate,
    MarksUpdate,
    PhaseBatchCreate,
    YearArchiveOut,
    YearCardOut,
    YearFilterOptionsOut,
    YearGridOut,
    YearPhaseCardCreate,
    YearPhaseOut,
)
from app.schemas.common import utc_now
from app.services.timeline_service import add_timeline_event
from app.utils.ids import new_id


async def assert_batch_owner(batch_id: str, owner_id: str) -> dict:
    batch = await get_database().batches.find_one({"id": batch_id})
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    if batch["owner_id"] != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Batch is not assigned to this owner")
    return batch


async def _validate_assignable_owner(owner_id: str | None) -> dict:
    if not owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="owner_id is required")
    user = await get_database().users.find_one({"id": owner_id})
    if not user or user.get("role") not in {Role.BATCH_OWNER.value, Role.LND_MANAGER.value}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid batch owner")
    if not user.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch owner is inactive")
    return user


def _parse_emails_csv(emails_csv: str) -> list[str]:
    parts = re.split(r"[\s,]+", emails_csv.strip())
    emails: list[str] = []
    invalid: list[str] = []
    pattern = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.IGNORECASE)
    for part in parts:
        if not part:
            continue
        normalized = part.strip().lower()
        if pattern.match(normalized):
            if normalized not in emails:
                emails.append(normalized)
        else:
            invalid.append(part.strip())
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid email values: {', '.join(invalid[:10])}",
        )
    if not emails:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid emails provided")
    return emails


def _resolve_reference_year(reference_year: int | None = None) -> int:
    return reference_year or datetime.now().year


def _normalize_phase_name(phase: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "_", phase.strip().upper()).strip("_")
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phase is required")
    return normalized


def _is_post_onboarding_phase(phase: str) -> bool:
    return _normalize_phase_name(phase) == ExamPhase.POST_ONBOARDING.value


def _year_status(year: int, reference_year: int) -> str:
    if year == reference_year:
        return "ACTIVE"
    if year == reference_year - 1:
        return "COMPLETED"
    if year < reference_year - 1:
        return "ARCHIVED"
    return "UPCOMING"


def _phase_sort_key(phase: str) -> int:
    normalized = _normalize_phase_name(phase)
    if normalized == ExamPhase.PRE_ONBOARDING.value:
        return 0
    if normalized == ExamPhase.POST_ONBOARDING.value:
        return 1
    return 10


def _parse_date(value: Any) -> Any:
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value).date()
    return value


def _is_post_onboarding_candidate(candidate: dict[str, Any]) -> bool:
    if candidate.get("offer_accepted"):
        return True
    return any(candidate.get(field) is not None for field in ("knowledge_check_python_score", "knowledge_check_java_score"))


def _candidate_matches_search(candidate: dict[str, Any], q: str | None) -> bool:
    if not q:
        return True
    search = q.strip().lower()
    return (
        search in str(candidate.get("name") or "").lower()
        or search in str(candidate.get("email") or "").lower()
        or search in str(candidate.get("college") or "").lower()
    )


async def _get_user_lookup() -> dict[str, dict[str, Any]]:
    users = await get_database().users.find({}).to_list(length=1000)
    return {user["id"]: user for user in users}


def _serialize_batch(batch: dict[str, Any], user_lookup: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    normalized = dict(batch)
    normalized["tech_stack"] = normalized.get("tech_stack") or []
    normalized["start_date"] = _parse_date(normalized.get("start_date"))
    normalized["end_date"] = _parse_date(normalized.get("end_date"))
    owner = (user_lookup or {}).get(normalized.get("owner_id"))
    normalized["owner_name"] = owner.get("name") if owner else None
    return normalized


async def _ensure_year_phase_card(year: int, phase: str) -> dict[str, Any]:
    phase = _normalize_phase_name(phase)
    db = get_database()
    existing = await db.year_phases.find_one({"year": year, "phase": phase})
    if existing:
        return existing

    now = utc_now()
    phase_card = {
        "id": new_id(),
        "year": year,
        "phase": phase,
        "created_at": now,
        "updated_at": now,
    }
    try:
        await db.year_phases.insert_one(phase_card)
    except Exception:
        existing = await db.year_phases.find_one({"year": year, "phase": phase})
        if existing:
            return existing
        raise
    return phase_card


async def create_year_phase_card(year: int, payload: YearPhaseCardCreate) -> dict[str, Any]:
    phase = _normalize_phase_name(payload.phase)
    phase_card = await _ensure_year_phase_card(year, phase)
    if payload.candidate_emails_csv:
        await import_phase_candidates_by_email(year, phase, CandidateEmailsImportRequest(emails_csv=payload.candidate_emails_csv))
    return await get_year_phase_card(year, phase)


async def get_year_phase_card(year: int, phase: str) -> dict[str, Any]:
    phase = _normalize_phase_name(phase)
    db = get_database()
    phase_card = await db.year_phases.find_one({"year": year, "phase": phase})
    if not phase_card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase card not found for year")

    user_lookup = await _get_user_lookup()
    phase_batches = await db.batches.find({"year": year, "phase": phase}).to_list(length=1000)
    phase_batch_ids = {batch["id"] for batch in phase_batches}
    all_candidates = await db.candidates.find({}).to_list(length=10000)
    candidates = [
        candidate
        for candidate in all_candidates
        if (
            candidate.get("eligible_phase") == phase
            and candidate.get("intake_year") in (year, None, 0)
            and (
                candidate.get("batch_id") is None
                or candidate.get("batch_id") in phase_batch_ids
            )
        )
    ]
    if _is_post_onboarding_phase(phase):
        candidates = [candidate for candidate in candidates if _is_post_onboarding_candidate(candidate)]

    return YearPhaseOut(
        id=phase_card["id"],
        year=year,
        phase=phase,
        status=_year_status(year, _resolve_reference_year()),
        candidate_count=len(candidates),
        unassigned_candidate_count=len([candidate for candidate in candidates if not candidate.get("batch_id")]),
        batch_count=len(phase_batches),
        batches=[_serialize_batch(batch, user_lookup) for batch in sorted(phase_batches, key=lambda item: item["name"].lower())],
        created_at=phase_card["created_at"],
        updated_at=phase_card["updated_at"],
    ).model_dump()


async def create_batch(payload: BatchCreate) -> dict:
    db = get_database()
    await _validate_assignable_owner(payload.owner_id)
    phase = _normalize_phase_name(payload.phase)
    await _ensure_year_phase_card(payload.year, phase)
    now = utc_now()
    batch = {
        "id": new_id(),
        "year": payload.year,
        "name": payload.name,
        "owner_id": payload.owner_id,
        "phase": phase,
        "start_date": None,
        "end_date": None,
        "tech_stack": [],
        "created_at": now,
        "updated_at": now,
    }
    await db.batches.insert_one(batch)
    user_lookup = await _get_user_lookup()
    return _serialize_batch(batch, user_lookup)


async def list_assigned_batches(owner_id: str) -> list[dict]:
    user_lookup = await _get_user_lookup()
    batches = await get_database().batches.find({"owner_id": owner_id}).to_list(length=1000)
    return [_serialize_batch(batch, user_lookup) for batch in batches]


async def list_eligible_candidates_for_batch_phase(
    batch_id: str,
    owner_id: str,
    q: str | None = None,
    tech_stack: str | None = None,
    college: str | None = None,
) -> list[dict]:
    batch = await assert_batch_owner(batch_id, owner_id)
    query: dict = {
        "batch_id": None,
        "status": CandidateStatus.ELIGIBLE.value,
        "eligible_phase": batch["phase"],
    }
    if tech_stack:
        query["tech_stack"] = tech_stack
    if college:
        query["college"] = college
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"college": {"$regex": q, "$options": "i"}},
        ]
    candidates = await get_database().candidates.find(query).to_list(length=10000)
    if _is_post_onboarding_phase(batch["phase"]):
        candidates = [candidate for candidate in candidates if _is_post_onboarding_candidate(candidate)]
    return [candidate for candidate in candidates if candidate.get("intake_year") in (None, batch["year"], 0)]


async def list_batches_readonly(user: dict) -> list[dict]:
    user_lookup = await _get_user_lookup()
    batches = await get_database().batches.find({}).to_list(length=1000)
    return [_serialize_batch(batch, user_lookup) for batch in batches]


async def list_assignable_batch_owners(current_user_id: str) -> list[dict]:
    users = await get_database().users.find({}).to_list(length=1000)
    assignable = []
    for user in users:
        if not user.get("is_active", False):
            continue
        if user.get("role") not in {Role.BATCH_OWNER.value, Role.LND_MANAGER.value}:
            continue
        if user["id"] != current_user_id and user.get("role") != Role.BATCH_OWNER.value:
            continue
        user.pop("hashed_password", None)
        assignable.append(user)
    return sorted(assignable, key=lambda item: (item["role"] != Role.LND_MANAGER.value, item.get("name", "").lower()))


async def update_batch_details(batch_id: str, owner_id: str, payload: BatchDetailsUpdate) -> dict:
    await assert_batch_owner(batch_id, owner_id)
    update = payload.model_dump()
    update["start_date"] = payload.start_date.isoformat()
    update["end_date"] = payload.end_date.isoformat()
    update["updated_at"] = utc_now()
    await get_database().batches.update_one({"id": batch_id}, {"$set": update})
    batch = await get_database().batches.find_one({"id": batch_id})
    for candidate in await get_database().candidates.find({"batch_id": batch_id}).to_list(length=10000):
        await add_timeline_event(
            candidate["id"],
            owner_id,
            TimelineEventType.BATCH_CONFIGURED,
            "Batch details configured",
            update,
        )
    user_lookup = await _get_user_lookup()
    return _serialize_batch(batch or {}, user_lookup)


async def create_candidate(payload: CandidateCreate) -> dict:
    now = utc_now()
    candidate = {
        "id": new_id(),
        "email": payload.email.lower(),
        "name": payload.name,
        "eligible_phase": _normalize_phase_name(payload.eligible_phase),
        "intake_year": payload.intake_year,
        "college": payload.college,
        "graduation_year": payload.graduation_year,
        "tech_stack": payload.tech_stack,
        "percentage": payload.percentage,
        "batch_id": None,
        "uid": None,
        "employee_email": None,
        "offer_accepted": payload.offer_accepted,
        "source": None,
        "status": CandidateStatus.ELIGIBLE.value,
        "pre_onboarding_score": None,
        "post_onboarding_score": None,
        "knowledge_check_python_score": None,
        "knowledge_check_java_score": None,
        "marks": {},
        "alternate_emails": [],
        "baseline_data": {},
        "baseline_email_map": {},
        "created_at": now,
        "updated_at": now,
    }
    try:
        await get_database().candidates.insert_one(candidate)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate email already exists") from exc
    return candidate


async def assign_candidates(batch_id: str, owner_id: str, candidate_ids: list[str]) -> list[dict]:
    batch = await assert_batch_owner(batch_id, owner_id)
    db = get_database()
    assigned: list[dict] = []
    for candidate_id in candidate_ids:
        candidate = await db.candidates.find_one({"id": candidate_id})
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate {candidate_id} not found")
        if candidate["eligible_phase"] != batch["phase"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Candidate {candidate_id} is not eligible for batch phase {batch['phase']}",
            )
        if _is_post_onboarding_phase(batch["phase"]) and not _is_post_onboarding_candidate(candidate):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Candidate {candidate_id} is not eligible for post-onboarding",
            )
        if candidate.get("batch_id") and candidate["batch_id"] != batch_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Candidate {candidate_id} already assigned")
        await db.candidates.update_one(
            {"id": candidate_id},
            {
                "$set": {
                    "batch_id": batch_id,
                    "status": CandidateStatus.ASSIGNED_TO_BATCH.value,
                    "updated_at": utc_now(),
                }
            },
        )
        updated = await db.candidates.find_one({"id": candidate_id})
        await add_timeline_event(
            candidate_id,
            owner_id,
            TimelineEventType.CANDIDATE_ASSIGNED,
            f"Candidate assigned to batch {batch_id}",
            {"batch_id": batch_id},
        )
        assigned.append(updated or {})
    return assigned


async def list_batch_candidates(
    batch_id: str,
    owner_id: str | None = None,
    q: str | None = None,
    status_filter: str | None = None,
    tech_stack: str | None = None,
    college: str | None = None,
    eligible_phase: str | None = None,
) -> list[dict]:
    if owner_id:
        await assert_batch_owner(batch_id, owner_id)
    query: dict = {"batch_id": batch_id}
    if status_filter:
        query["status"] = status_filter
    if tech_stack:
        query["tech_stack"] = tech_stack
    if college:
        query["college"] = college
    if eligible_phase:
        query["eligible_phase"] = eligible_phase
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"college": {"$regex": q, "$options": "i"}},
        ]
    return await get_database().candidates.find(query).to_list(length=10000)


async def update_candidate_marks(batch_id: str, candidate_id: str, owner_id: str, payload: MarksUpdate) -> dict:
    await assert_batch_owner(batch_id, owner_id)
    candidate = await get_database().candidates.find_one({"id": candidate_id, "batch_id": batch_id})
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found in this batch")
    marks = {**candidate.get("marks", {}), **payload.marks}
    await get_database().candidates.update_one({"id": candidate_id}, {"$set": {"marks": marks, "updated_at": utc_now()}})
    await add_timeline_event(
        candidate_id,
        owner_id,
        TimelineEventType.MARKS_UPDATED,
        "Candidate marks manually updated",
        {"marks": payload.marks},
    )
    return await get_database().candidates.find_one({"id": candidate_id}) or {}


async def update_candidate_employment_details(
    batch_id: str,
    candidate_id: str,
    owner_id: str,
    payload: CandidateEmploymentUpdate,
) -> dict:
    batch = await assert_batch_owner(batch_id, owner_id)
    if not _is_post_onboarding_phase(batch["phase"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UID and employee email can only be updated for post-onboarding batches",
        )
    candidate = await get_database().candidates.find_one({"id": candidate_id, "batch_id": batch_id})
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found in this batch")
    await get_database().candidates.update_one(
        {"id": candidate_id},
        {
            "$set": {
                "uid": payload.uid,
                "employee_email": payload.employee_email.lower(),
                "updated_at": utc_now(),
            }
        },
    )
    await add_timeline_event(
        candidate_id,
        owner_id,
        TimelineEventType.EMPLOYMENT_DETAILS_UPDATED,
        "Candidate UID and employee email updated",
        {"uid": payload.uid, "employee_email": payload.employee_email.lower()},
    )
    return await get_database().candidates.find_one({"id": candidate_id}) or {}


async def get_candidate_timeline(candidate_id: str, actor_id: str, require_owned: bool = True) -> list[dict]:
    db = get_database()
    candidate = await db.candidates.find_one({"id": candidate_id})
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    if require_owned:
        if not candidate.get("batch_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidate is not assigned")
        await assert_batch_owner(candidate["batch_id"], actor_id)
    return await db.timeline_events.find({"candidate_id": candidate_id}).sort("created_at", 1).to_list(length=10000)


async def get_batch_candidate_timeline(batch_id: str, candidate_id: str) -> list[dict]:
    db = get_database()
    batch = await db.batches.find_one({"id": batch_id})
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    candidate = await db.candidates.find_one({"id": candidate_id})
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    if candidate.get("batch_id") != batch_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate is not assigned to this batch",
        )
    return await db.timeline_events.find({"candidate_id": candidate_id}).sort("created_at", 1).to_list(length=10000)


async def import_phase_candidates_by_email(year: int, phase: str, payload: CandidateEmailsImportRequest) -> dict[str, Any]:
    phase = _normalize_phase_name(phase)
    await _ensure_year_phase_card(year, phase)
    db = get_database()
    emails = _parse_emails_csv(payload.emails_csv)
    created = 0
    updated = 0
    skipped: list[dict[str, str]] = []

    for email in emails:
        candidate = await db.candidates.find_one({"email": email})
        if not candidate:
            if _is_post_onboarding_phase(phase):
                skipped.append({"email": email, "reason": "Candidate does not exist for direct post-onboarding assignment"})
                continue
            now = utc_now()
            await db.insert_candidate_row(
                {
                    "id": new_id(),
                    "email": email,
                    "name": email.split("@")[0],
                    "eligible_phase": phase,
                    "intake_year": year,
                    "college": None,
                    "graduation_year": None,
                    "tech_stack": None,
                    "percentage": None,
                    "batch_id": None,
                    "uid": None,
                    "employee_email": None,
                    "offer_accepted": False,
                    "source": "MANUAL_PHASE_IMPORT",
                    "status": CandidateStatus.ELIGIBLE.value,
                    "pre_onboarding_score": None,
                    "post_onboarding_score": None,
                    "knowledge_check_python_score": None,
                    "knowledge_check_java_score": None,
                    "marks": {},
                    "alternate_emails": [],
                    "baseline_data": {},
                    "baseline_email_map": {},
                    "created_at": now,
                    "updated_at": now,
                }
            )
            created += 1
            continue

        if candidate.get("batch_id"):
            skipped.append({"email": email, "reason": "Candidate is already assigned to a batch"})
            continue

        if _is_post_onboarding_phase(phase) and not _is_post_onboarding_candidate(candidate):
            skipped.append({"email": email, "reason": "Candidate must have offer accepted or knowledge check score for post-onboarding"})
            continue

        updates = {"eligible_phase": phase, "updated_at": utc_now(), "intake_year": year}
        await db.update_candidate_row({"id": candidate["id"]}, updates)
        updated += 1

    return CandidateEmailsImportResult(
        year=year,
        phase=phase,
        processed_emails=len(emails),
        created_candidates=created,
        updated_candidates=updated,
        skipped=skipped,
    ).model_dump()


async def list_phase_candidates(
    year: int,
    phase: str,
    *,
    q: str | None = None,
    tech_stack: str | None = None,
    college: str | None = None,
) -> list[dict]:
    phase = _normalize_phase_name(phase)
    await _ensure_year_phase_card(year, phase)
    query: dict[str, Any] = {
        "eligible_phase": phase,
        "batch_id": None,
        "status": CandidateStatus.ELIGIBLE.value,
    }
    if tech_stack:
        query["tech_stack"] = tech_stack
    if college:
        query["college"] = college
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"college": {"$regex": q, "$options": "i"}},
        ]
    candidates = await get_database().candidates.find(query).to_list(length=10000)
    if _is_post_onboarding_phase(phase):
        candidates = [candidate for candidate in candidates if _is_post_onboarding_candidate(candidate)]
    return [candidate for candidate in candidates if candidate.get("intake_year") in (None, year, 0)]


async def create_phase_batch(year: int, phase: str, payload: PhaseBatchCreate) -> dict:
    phase = _normalize_phase_name(phase)
    await _ensure_year_phase_card(year, phase)
    await _validate_assignable_owner(payload.owner_id)
    return await create_batch(
        BatchCreate(
            year=year,
            name=payload.name,
            owner_id=payload.owner_id,
            phase=phase,
        )
    )


async def assign_batch_owner(batch_id: str, payload: BatchOwnerAssignRequest) -> dict:
    await _validate_assignable_owner(payload.owner_id)
    batch = await get_database().batches.find_one({"id": batch_id})
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    await get_database().batches.update_one(
        {"id": batch_id},
        {"$set": {"owner_id": payload.owner_id, "updated_at": utc_now()}},
    )
    updated = await get_database().batches.find_one({"id": batch_id}) or {}
    user_lookup = await _get_user_lookup()
    return _serialize_batch(updated, user_lookup)


async def assign_candidates_to_batch_by_email(batch_id: str, payload: CandidateEmailsImportRequest) -> dict[str, Any]:
    db = get_database()
    batch = await db.batches.find_one({"id": batch_id})
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    emails = _parse_emails_csv(payload.emails_csv)
    assigned = 0
    skipped: list[dict[str, str]] = []

    for email in emails:
        candidate = await db.candidates.find_one({"email": email})
        if not candidate:
            skipped.append({"email": email, "reason": "Candidate not found"})
            continue
        if candidate.get("batch_id") and candidate.get("batch_id") != batch_id:
            skipped.append({"email": email, "reason": "Candidate already assigned to another batch"})
            continue
        if candidate.get("eligible_phase") != batch["phase"]:
            skipped.append({"email": email, "reason": "Candidate phase does not match batch phase"})
            continue
        if _is_post_onboarding_phase(batch["phase"]) and not _is_post_onboarding_candidate(candidate):
            skipped.append({"email": email, "reason": "Candidate is not eligible for post-onboarding"})
            continue
        await db.candidates.update_one(
            {"id": candidate["id"]},
            {"$set": {"batch_id": batch_id, "status": CandidateStatus.ASSIGNED_TO_BATCH.value, "updated_at": utc_now()}},
        )
        assigned += 1
        await add_timeline_event(
            candidate["id"],
            batch["owner_id"],
            TimelineEventType.CANDIDATE_ASSIGNED,
            f"Candidate assigned to batch {batch_id}",
            {"batch_id": batch_id},
        )

    return CandidateEmailsImportResult(
        batch_id=batch_id,
        processed_emails=len(emails),
        assigned=assigned,
        skipped=skipped,
    ).model_dump()


def _candidate_visible_in_year(candidate: dict[str, Any], year: int, year_batch_ids: set[str]) -> bool:
    if candidate.get("batch_id") in year_batch_ids:
        return True
    return candidate.get("batch_id") is None and candidate.get("intake_year") in (year, None, 0)


async def _build_year_card(
    year: int,
    reference_year: int,
    year_phases: list[dict[str, Any]],
    batches: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> YearCardOut:
    user_lookup = await _get_user_lookup()
    created_phase_codes = sorted({phase_card["phase"] for phase_card in year_phases}, key=lambda item: (_phase_sort_key(item), item))
    phase_cards = []

    for phase_card in sorted(year_phases, key=lambda item: _phase_sort_key(item["phase"])):
        phase_batches = [batch for batch in batches if batch.get("phase") == phase_card["phase"]]
        phase_batch_ids = {batch["id"] for batch in phase_batches}
        phase_candidates = [
            candidate
            for candidate in candidates
            if candidate.get("eligible_phase") == phase_card["phase"]
            and (
                candidate.get("batch_id") in phase_batch_ids
                or (candidate.get("batch_id") is None and candidate.get("intake_year") in (year, None, 0))
            )
        ]
        if _is_post_onboarding_phase(phase_card["phase"]):
            phase_candidates = [candidate for candidate in phase_candidates if _is_post_onboarding_candidate(candidate)]
        phase_cards.append(
            YearPhaseOut(
                id=phase_card["id"],
                year=year,
                phase=phase_card["phase"],
                status=_year_status(year, reference_year),
                candidate_count=len(phase_candidates),
                unassigned_candidate_count=len([candidate for candidate in phase_candidates if not candidate.get("batch_id")]),
                batch_count=len(phase_batches),
                batches=[_serialize_batch(batch, user_lookup) for batch in sorted(phase_batches, key=lambda item: item["name"].lower())],
                created_at=phase_card["created_at"],
                updated_at=phase_card["updated_at"],
            )
        )

    return YearCardOut(
        year=year,
        status=_year_status(year, reference_year),
        candidate_count=len(candidates),
        batch_count=len(batches),
        phases_created=created_phase_codes,
        phases=phase_cards,
        batches=[_serialize_batch(batch, user_lookup) for batch in sorted(batches, key=lambda item: (_phase_sort_key(item["phase"]), item["name"].lower()))],
    )


async def get_batch_grid(reference_year: int | None = None) -> YearGridOut:
    db = get_database()
    resolved_reference_year = _resolve_reference_year(reference_year)
    years = [resolved_reference_year, resolved_reference_year - 1, resolved_reference_year - 2, resolved_reference_year - 3]

    all_phase_cards = await db.year_phases.find({}).to_list(length=1000)
    all_batches = await db.batches.find({}).to_list(length=1000)
    all_candidates = await db.candidates.find({}).to_list(length=10000)

    cards_by_year: dict[int, YearCardOut] = {}
    for year in years:
        year_phase_cards = [phase_card for phase_card in all_phase_cards if phase_card.get("year") == year]
        year_batches = [batch for batch in all_batches if batch.get("year") == year]
        year_batch_ids = {batch["id"] for batch in year_batches}
        year_candidates = [candidate for candidate in all_candidates if _candidate_visible_in_year(candidate, year, year_batch_ids)]
        cards_by_year[year] = await _build_year_card(year, resolved_reference_year, year_phase_cards, year_batches, year_candidates)

    return YearGridOut(
        reference_year=resolved_reference_year,
        active_year=cards_by_year.get(resolved_reference_year),
        completed_year=cards_by_year.get(resolved_reference_year - 1),
        archive_years=[cards_by_year[year] for year in years[2:]],
    )


async def get_year_archive(
    year: int,
    *,
    q: str | None = None,
    phase: str | None = None,
    candidate_status: str | None = None,
    tech_stack: str | None = None,
    college: str | None = None,
    reference_year: int | None = None,
) -> YearArchiveOut:
    db = get_database()
    resolved_reference_year = _resolve_reference_year(reference_year)
    user_lookup = await _get_user_lookup()

    batches = await db.batches.find({"year": year}).to_list(length=1000)
    batch_ids = {batch["id"] for batch in batches}
    candidates = [
        candidate
        for candidate in await db.candidates.find({}).to_list(length=10000)
        if candidate.get("batch_id") in batch_ids
    ]

    filters = YearFilterOptionsOut(
        phases=sorted({batch["phase"] for batch in batches}, key=lambda item: (_phase_sort_key(item), item)),
        candidate_statuses=sorted({candidate["status"] for candidate in candidates}),
        colleges=sorted({candidate["college"] for candidate in candidates if candidate.get("college")}),
        tech_stacks=sorted({candidate["tech_stack"] for candidate in candidates if candidate.get("tech_stack")}),
    )

    filtered_batches = batches
    if phase:
        filtered_batches = [batch for batch in filtered_batches if batch.get("phase") == phase]

    visible_batch_ids = {batch["id"] for batch in filtered_batches}
    filtered_candidates = [candidate for candidate in candidates if candidate.get("batch_id") in visible_batch_ids]

    if candidate_status:
        filtered_candidates = [candidate for candidate in filtered_candidates if candidate.get("status") == candidate_status]
    if tech_stack:
        filtered_candidates = [candidate for candidate in filtered_candidates if candidate.get("tech_stack") == tech_stack]
    if college:
        filtered_candidates = [candidate for candidate in filtered_candidates if candidate.get("college") == college]
    if q:
        filtered_candidates = [candidate for candidate in filtered_candidates if _candidate_matches_search(candidate, q)]

    return YearArchiveOut(
        year=year,
        status=_year_status(year, resolved_reference_year),
        candidate_count=len(filtered_candidates),
        batch_count=len(filtered_batches),
        filters=filters,
        candidates=filtered_candidates,
        batches=[_serialize_batch(batch, user_lookup) for batch in sorted(filtered_batches, key=lambda item: (_phase_sort_key(item["phase"]), item["name"].lower()))],
    )


async def get_year_summary(year: int, reference_year: int | None = None) -> YearArchiveOut:
    return await get_year_archive(year, reference_year=reference_year)


async def list_year_phases(year: int, reference_year: int | None = None) -> YearCardOut:
    db = get_database()
    resolved_reference_year = _resolve_reference_year(reference_year)
    year_phase_cards = await db.year_phases.find({"year": year}).to_list(length=1000)
    year_batches = await db.batches.find({"year": year}).to_list(length=1000)
    batch_ids = {batch["id"] for batch in year_batches}
    year_candidates = [
        candidate
        for candidate in await db.candidates.find({}).to_list(length=10000)
        if _candidate_visible_in_year(candidate, year, batch_ids)
    ]
    return await _build_year_card(year, resolved_reference_year, year_phase_cards, year_batches, year_candidates)


async def list_year_archives(reference_year: int | None = None) -> list[YearCardOut]:
    grid = await get_batch_grid(reference_year)
    return grid.archive_years


async def get_past_year_archive(
    year: int,
    *,
    q: str | None = None,
    phase: str | None = None,
    candidate_status: str | None = None,
    tech_stack: str | None = None,
    college: str | None = None,
    reference_year: int | None = None,
) -> YearArchiveOut:
    resolved_reference_year = _resolve_reference_year(reference_year)
    if year >= resolved_reference_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Year archives only contain past years",
        )
    return await get_year_archive(
        year,
        q=q,
        phase=phase,
        candidate_status=candidate_status,
        tech_stack=tech_stack,
        college=college,
        reference_year=resolved_reference_year,
    )
