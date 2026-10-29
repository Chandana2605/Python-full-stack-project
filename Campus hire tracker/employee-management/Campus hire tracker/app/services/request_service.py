from fastapi import HTTPException, status

from app.core.enums import CandidateStatus, RequestStatus, RequestType, TimelineEventType
from app.db.postgresql import get_database
from app.schemas.batches import ChangeRequestCreate, ChangeRequestReview, RuleChangeRequestCreate
from app.schemas.common import utc_now
from app.services.batch_service import assert_batch_owner
from app.services.timeline_service import add_timeline_event
from app.utils.ids import new_id


async def create_change_request(batch_id: str, owner_id: str, payload: ChangeRequestCreate) -> dict:
    await assert_batch_owner(batch_id, owner_id)
    db = get_database()
    candidate = await db.candidates.find_one({"email": payload.candidate_email.lower(), "batch_id": batch_id})
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found in this batch")
    existing = await db.change_requests.find_one({"candidate_id": candidate["id"], "status": RequestStatus.PENDING.value})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pending request already exists")
    now = utc_now()
    request = {
        "id": new_id(),
        "candidate_id": candidate["id"],
        "candidate_email": candidate["email"],
        "batch_id": batch_id,
        "requested_by": owner_id,
        "request_type": payload.request_type.value,
        "reason": payload.reason,
        "status": RequestStatus.PENDING.value,
        "reviewer_id": None,
        "reviewer_comment": None,
        "created_at": now,
        "reviewed_at": None,
    }
    await db.change_requests.insert_one(request)
    candidate_status = (
        CandidateStatus.DROPOUT_REQUESTED
        if payload.request_type.value == "DROPOUT"
        else CandidateStatus.RESIGNATION_REQUESTED
    )
    await db.candidates.update_one(
        {"id": candidate["id"]}, {"$set": {"status": candidate_status.value, "updated_at": now}}
    )
    await add_timeline_event(
        candidate["id"],
        owner_id,
        TimelineEventType[f"{payload.request_type.value}_REQUESTED"],
        f"{payload.request_type.value.title()} request submitted",
        {"reason": payload.reason, "request_id": request["id"]},
    )
    return request


async def create_rule_change_request(requested_by: str, payload: RuleChangeRequestCreate) -> dict:
    db = get_database()
    batch = await db.batches.find_one({"id": payload.batch_id})
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    existing = await db.change_requests.find_one(
        {
            "batch_id": payload.batch_id,
            "request_type": RequestType.RULE_CHANGE.value,
            "status": RequestStatus.PENDING.value,
        }
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pending rule change request already exists for this batch")

    now = utc_now()
    request = {
        "id": new_id(),
        "candidate_id": None,
        "candidate_email": None,
        "batch_id": payload.batch_id,
        "requested_by": requested_by,
        "request_type": RequestType.RULE_CHANGE.value,
        "exam_type": payload.exam_type.value,
        "custom_exam_name": payload.custom_exam_name,
        "reason": payload.reason,
        "current_pass_percentage": payload.current_pass_percentage,
        "requested_pass_percentage": payload.requested_pass_percentage,
        "status": RequestStatus.PENDING.value,
        "reviewer_id": None,
        "reviewer_comment": None,
        "created_at": now,
        "reviewed_at": None,
    }
    await db.change_requests.insert_one(request)
    return request


async def list_change_requests(status_filter: RequestStatus | None = None) -> list[dict]:
    query = {"status": status_filter.value} if status_filter else {}
    return await get_database().change_requests.find(query).to_list(length=10000)


async def list_rule_change_requests(status_filter: RequestStatus | None = None) -> list[dict]:
    query: dict = {"request_type": RequestType.RULE_CHANGE.value}
    if status_filter:
        query["status"] = status_filter.value
    return await get_database().change_requests.find(query).to_list(length=10000)


async def list_owner_change_requests(owner_id: str, status_filter: RequestStatus | None = None) -> list[dict]:
    query: dict = {"requested_by": owner_id}
    if status_filter:
        query["status"] = status_filter.value
    return await get_database().change_requests.find(query).to_list(length=10000)


async def review_change_request(request_id: str, reviewer_id: str, payload: ChangeRequestReview) -> dict:
    if payload.status == RequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review must approve or reject")
    db = get_database()
    request = await db.change_requests.find_one({"id": request_id})
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if request["status"] != RequestStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request already reviewed")
    now = utc_now()
    await db.change_requests.update_one(
        {"id": request_id},
        {
            "$set": {
                "status": payload.status.value,
                "reviewer_id": reviewer_id,
                "reviewer_comment": payload.reviewer_comment,
                "reviewed_at": now,
            }
        },
    )
    if payload.status == RequestStatus.REJECTED:
        await db.candidates.update_one(
            {"id": request["candidate_id"]},
            {"$set": {"status": CandidateStatus.ASSIGNED_TO_BATCH.value, "updated_at": now}},
        )
    await add_timeline_event(
        request["candidate_id"],
        reviewer_id,
        TimelineEventType.REQUEST_REVIEWED,
        f"Request {request_id} {payload.status.value.lower()}",
        {"reviewer_comment": payload.reviewer_comment},
    )
    return await db.change_requests.find_one({"id": request_id}) or {}
