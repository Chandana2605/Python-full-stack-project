from datetime import date, datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from ..exceptions.http_exceptions import bad_request_exception, conflict_exception, forbidden_exception, not_found_exception
from ..models.batch import BatchCreate, BatchOut, BatchUpdate
from .user_service import serialize_document


class BatchService:
    def __init__(self, db):
        self.db = db

    async def create_batch(self, payload: BatchCreate, created_by: str) -> BatchOut:
        now = datetime.now(timezone.utc)
        if payload.owner_id:
            owner = await self.db.users.find_one({"_id": self._oid(payload.owner_id)})
            if not owner:
                raise not_found_exception("Batch owner not found")
            if owner["role"] not in {"admin", "batch_owner"}:
                raise bad_request_exception("Assigned owner must be admin or batch owner")

        document = {
            **self._normalize_batch_data(payload.model_dump()),
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self.db.batches.insert_one(document)
        except DuplicateKeyError as exc:
            raise conflict_exception("Batch with same year, phase, and name already exists") from exc

        created = await self.db.batches.find_one({"_id": result.inserted_id})
        return await self._enrich_batch(created)

    async def list_batches(self, current_user: dict) -> list[BatchOut]:
        query = {}
        if current_user["role"] == "batch_owner":
            query["owner_id"] = current_user["id"]
        batches = await self.db.batches.find(query).sort([("year", -1), ("phase", 1), ("name", 1)]).to_list(length=1000)
        return [await self._enrich_batch(batch) for batch in batches]

    async def update_batch(self, batch_id: str, payload: BatchUpdate, current_user: dict) -> BatchOut:
        batch = await self.db.batches.find_one({"_id": self._oid(batch_id)})
        if not batch:
            raise not_found_exception("Batch not found")
        self._enforce_batch_access(batch, current_user, allow_admin=True)

        update_data = {
            key: value
            for key, value in self._normalize_batch_data(payload.model_dump()).items()
            if value is not None
        }
        if not update_data:
            raise bad_request_exception("No update fields provided")
        update_data["updated_at"] = datetime.now(timezone.utc)
        await self.db.batches.update_one({"_id": batch["_id"]}, {"$set": update_data})
        updated = await self.db.batches.find_one({"_id": batch["_id"]})
        return await self._enrich_batch(updated)

    async def assign_candidates(self, batch_id: str, candidate_ids: list[str], current_user: dict) -> dict:
        batch = await self.db.batches.find_one({"_id": self._oid(batch_id)})
        if not batch:
            raise not_found_exception("Batch not found")
        self._enforce_batch_access(batch, current_user, allow_admin=True)

        await self.db.candidates.update_many(
            {"_id": {"$in": [self._oid(candidate_id) for candidate_id in candidate_ids]}},
            {"$set": {"batch_id": str(batch["_id"]), "phase": batch["phase"], "updated_at": datetime.now(timezone.utc)}},
        )
        return {"message": f"Assigned {len(candidate_ids)} candidates to batch"}

    async def export_batch_candidates(self, batch_id: str, current_user: dict) -> list[dict]:
        batch = await self.db.batches.find_one({"_id": self._oid(batch_id)})
        if not batch:
            raise not_found_exception("Batch not found")
        self._enforce_batch_access(batch, current_user, allow_admin=True, allow_program_manager=True)

        candidates = await self.db.candidates.find({"batch_id": str(batch["_id"])}).sort("name", 1).to_list(length=5000)
        return [serialize_document(candidate) for candidate in candidates]

    async def _enrich_batch(self, batch: dict) -> BatchOut:
        owner_name = None
        if batch.get("owner_id"):
            owner = await self.db.users.find_one({"_id": self._oid(batch["owner_id"])})
            owner_name = owner["name"] if owner else None
        payload = serialize_document(batch)
        payload["owner_name"] = owner_name
        return BatchOut(**payload)

    @staticmethod
    def _enforce_batch_access(batch: dict, current_user: dict, allow_admin: bool = False, allow_program_manager: bool = False) -> None:
        if allow_admin and current_user["role"] == "admin":
            return
        if allow_program_manager and current_user["role"] == "program_manager":
            return
        if current_user["role"] == "batch_owner" and batch.get("owner_id") == current_user["id"]:
            return
        raise forbidden_exception("You can only access your assigned batches")

    @staticmethod
    def _oid(value: str) -> ObjectId:
        try:
            return ObjectId(value)
        except Exception as exc:
            raise bad_request_exception("Invalid identifier") from exc

    @staticmethod
    def _normalize_batch_data(data: dict) -> dict:
        normalized = dict(data)
        for field in ("start_date", "end_date"):
            value = normalized.get(field)
            if isinstance(value, date) and not isinstance(value, datetime):
                normalized[field] = datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
        return normalized
