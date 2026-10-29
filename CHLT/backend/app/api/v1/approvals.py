from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, status

from .users import get_database, require_roles
from ...exceptions.http_exceptions import bad_request_exception, forbidden_exception, not_found_exception
from ...models.approval import ApprovalDecision, ApprovalOut, ApprovalRequestCreate
from ...services.approval_service import ApprovalService

router = APIRouter(prefix="/approvals", tags=["Approvals"])


def get_approval_service() -> ApprovalService:
    return ApprovalService(get_database())


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as exc:
        raise bad_request_exception("Invalid identifier") from exc


@router.post("", response_model=ApprovalOut, status_code=status.HTTP_201_CREATED)
async def create_rule_change_request(
    payload: ApprovalRequestCreate,
    current_user: dict = Depends(require_roles("admin")),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalOut:
    return await service.create_request(payload, current_user["id"])


@router.get("", response_model=list[ApprovalOut])
async def list_rule_change_requests(
    status: str | None = None,
    _: dict = Depends(require_roles("admin", "program_manager")),
    service: ApprovalService = Depends(get_approval_service),
) -> list[ApprovalOut]:
    return await service.list_requests(status)


@router.post("/{approval_id}/decision", response_model=ApprovalOut)
async def decide_rule_change_request(
    approval_id: str,
    payload: ApprovalDecision,
    current_user: dict = Depends(require_roles("program_manager")),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalOut:
    return await service.decide_request(approval_id, payload, current_user["id"])


@router.post("/dropouts/{candidate_id}/mark")
async def mark_dropout(
    candidate_id: str,
    reason: str,
    current_user: dict = Depends(require_roles("admin", "batch_owner")),
) -> dict:
    db = get_database()
    candidate = await db.candidates.find_one({"_id": _oid(candidate_id)})
    if not candidate:
        raise not_found_exception("Candidate not found")

    if current_user["role"] == "batch_owner":
        batch = await db.batches.find_one({"_id": _oid(candidate["batch_id"])}) if candidate.get("batch_id") else None
        if not batch or batch.get("owner_id") != current_user["id"]:
            raise forbidden_exception("You can only mark dropout for candidates in your batches")

    now = datetime.now(timezone.utc)
    await db.dropouts.update_one(
        {"candidate_id": candidate_id, "is_active": True},
        {
            "$set": {
                "candidate_id": candidate_id,
                "candidate_year": candidate["year"],
                "reason": reason,
                "requested_by": current_user["id"],
                "finalized_by": current_user["id"] if current_user["role"] == "admin" else None,
                "is_active": True,
                "status": "finalized" if current_user["role"] == "admin" else "pending_admin_review",
                "created_at": now,
                "updated_at": now,
            }
        },
        upsert=True,
    )
    await db.candidates.update_one(
        {"_id": candidate["_id"]},
        {"$set": {"status": "dropout_finalized" if current_user["role"] == "admin" else "dropout_pending", "updated_at": now}},
    )
    return {"message": "Dropout status updated"}


@router.post("/dropouts/{candidate_id}/revoke")
async def revoke_dropout(
    candidate_id: str,
    current_user: dict = Depends(require_roles("admin")),
) -> dict:
    db = get_database()
    candidate = await db.candidates.find_one({"_id": _oid(candidate_id)})
    if not candidate:
        raise not_found_exception("Candidate not found")

    now = datetime.now(timezone.utc)
    await db.dropouts.update_many({"candidate_id": candidate_id, "is_active": True}, {"$set": {"is_active": False, "updated_at": now}})
    await db.candidates.update_one({"_id": candidate["_id"]}, {"$set": {"status": "post_onboarding", "updated_at": now}})
    return {"message": "Dropout revoked successfully"}
