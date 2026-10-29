from datetime import datetime, timezone

from bson import ObjectId

from ..exceptions.http_exceptions import bad_request_exception, not_found_exception
from ..models.approval import ApprovalDecision, ApprovalOut, ApprovalRequestCreate
from .user_service import serialize_document


class ApprovalService:
    def __init__(self, db):
        self.db = db

    async def create_request(self, payload: ApprovalRequestCreate, requested_by: str) -> ApprovalOut:
        now = datetime.now(timezone.utc)
        result = await self.db.approvals.insert_one(
            {
                **payload.model_dump(),
                "status": "pending",
                "requested_by": requested_by,
                "reviewed_by": None,
                "review_reason": None,
                "created_at": now,
                "reviewed_at": None,
            }
        )
        created = await self.db.approvals.find_one({"_id": result.inserted_id})
        return ApprovalOut(**serialize_document(created))

    async def list_requests(self, status: str | None = None) -> list[ApprovalOut]:
        query = {"status": status} if status else {}
        approvals = await self.db.approvals.find(query).sort("created_at", -1).to_list(length=1000)
        return [ApprovalOut(**serialize_document(item)) for item in approvals]

    async def decide_request(self, approval_id: str, payload: ApprovalDecision, reviewer_id: str) -> ApprovalOut:
        approval = await self.db.approvals.find_one({"_id": self._oid(approval_id)})
        if not approval:
            raise not_found_exception("Approval request not found")
        if approval["status"] != "pending":
            raise bad_request_exception("Approval request has already been reviewed")

        await self.db.approvals.update_one(
            {"_id": approval["_id"]},
            {"$set": {"status": payload.decision, "reviewed_by": reviewer_id, "review_reason": payload.reason, "reviewed_at": datetime.now(timezone.utc)}},
        )
        updated = await self.db.approvals.find_one({"_id": approval["_id"]})
        return ApprovalOut(**serialize_document(updated))

    @staticmethod
    def _oid(value: str) -> ObjectId:
        try:
            return ObjectId(value)
        except Exception as exc:
            raise bad_request_exception("Invalid identifier") from exc
