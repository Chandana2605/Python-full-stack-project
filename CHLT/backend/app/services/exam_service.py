from datetime import datetime, timezone

from bson import ObjectId

from ..exceptions.http_exceptions import bad_request_exception, forbidden_exception, not_found_exception
from ..models.exam import ExamCreate, ExamOut, ExamUpdate
from .user_service import serialize_document


class ExamService:
    def __init__(self, db):
        self.db = db

    async def create_exam(self, payload: ExamCreate, current_user: dict) -> ExamOut:
        candidate = await self.db.candidates.find_one({"_id": self._oid(payload.candidate_id)})
        if not candidate:
            raise not_found_exception("Candidate not found")
        await self._enforce_candidate_access(candidate, current_user)
        self._validate_exam_rules(payload)

        now = datetime.now(timezone.utc)
        document = {**payload.model_dump(), "badge": self._determine_badge(payload), "created_by": current_user["id"], "created_at": now, "updated_at": now}
        result = await self.db.exams.insert_one(document)
        await self._sync_candidate_after_exam(candidate, document)
        created = await self.db.exams.find_one({"_id": result.inserted_id})
        return ExamOut(**serialize_document(created))

    async def create_or_update_exam(self, payload: ExamCreate, current_user: dict) -> ExamOut:
        existing = await self.db.exams.find_one(
            {
                "candidate_id": payload.candidate_id,
                "exam_type": payload.exam_type,
                "attempt_number": payload.attempt_number,
            }
        )
        if existing:
            return await self.update_exam(
                str(existing["_id"]),
                ExamUpdate(
                    score=payload.score,
                    attended=payload.attended,
                    passed=payload.passed,
                    status=payload.status,
                ),
                current_user,
            )
        return await self.create_exam(payload, current_user)

    async def update_exam(self, exam_id: str, payload: ExamUpdate, current_user: dict) -> ExamOut:
        exam = await self.db.exams.find_one({"_id": self._oid(exam_id)})
        if not exam:
            raise not_found_exception("Exam not found")
        candidate = await self.db.candidates.find_one({"_id": self._oid(exam["candidate_id"])})
        if not candidate:
            raise not_found_exception("Candidate not found")
        await self._enforce_candidate_access(candidate, current_user)

        update_data = {key: value for key, value in payload.model_dump().items() if value is not None}
        if not update_data:
            raise bad_request_exception("No update fields provided")

        merged = {**exam, **update_data}
        update_data["badge"] = self._determine_badge(merged)
        update_data["updated_at"] = datetime.now(timezone.utc)
        await self.db.exams.update_one({"_id": exam["_id"]}, {"$set": update_data})
        await self._sync_candidate_after_exam(candidate, {**exam, **update_data})
        updated = await self.db.exams.find_one({"_id": exam["_id"]})
        return ExamOut(**serialize_document(updated))

    async def list_exams(self, current_user: dict, exam_type: str | None = None) -> list[ExamOut]:
        query = {"exam_type": exam_type} if exam_type else {}
        if current_user["role"] == "batch_owner":
            owned_batches = await self.db.batches.find({"owner_id": current_user["id"]}).to_list(length=1000)
            query["batch_id"] = {"$in": [str(batch["_id"]) for batch in owned_batches]}

        exams = await self.db.exams.find(query).sort("created_at", -1).to_list(length=5000)
        return [ExamOut(**serialize_document(exam)) for exam in exams]

    async def _sync_candidate_after_exam(self, candidate: dict, exam: dict) -> None:
        badge = exam.get("badge")
        status = candidate.get("status", "master_imported")
        if badge == "eligible_for_offer":
            status = "eligible_for_offer"
        elif badge == "recommended_loi_cancellation":
            status = "recommended_loi_cancellation"
        elif badge == "deployment_ready":
            status = "deployment_ready"
        elif badge == "referred_to_hr":
            status = "referred_to_hr"

        await self.db.candidates.update_one({"_id": candidate["_id"]}, {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}})
        await self.db.audit_logs.insert_one(
            {
                "entity_type": "candidate",
                "entity_id": str(candidate["_id"]),
                "action": "exam_updated",
                "message": f"{exam['exam_type']} attempt {exam['attempt_number']} recorded with badge {badge or 'none'}",
                "created_by": exam.get("created_by"),
                "created_at": datetime.now(timezone.utc),
            }
        )

    async def _enforce_candidate_access(self, candidate: dict, current_user: dict) -> None:
        if current_user["role"] in {"admin", "program_manager"}:
            return
        if not candidate.get("batch_id"):
            raise forbidden_exception("Candidate is not assigned to a batch")
        batch = await self.db.batches.find_one({"_id": self._oid(candidate["batch_id"])})
        if batch and batch.get("owner_id") == current_user["id"]:
            return
        raise forbidden_exception("You can only manage exams for candidates in your batches")

    @staticmethod
    def _validate_exam_rules(exam: ExamCreate) -> None:
        if exam.exam_type == "knowledge_check" and not exam.coding_name:
            raise bad_request_exception("Coding name is required for knowledge checks")
        if exam.attended is False and exam.status != "not_attended":
            raise bad_request_exception("Not attended exams must use status 'not_attended'")
        if exam.attempt_number > 1 and exam.passed:
            raise bad_request_exception("Reattempt is only allowed for failed cases")

    @staticmethod
    def _determine_badge(exam: dict | ExamCreate) -> str | None:
        score = exam.get("score") if isinstance(exam, dict) else exam.score
        passed = exam.get("passed") if isinstance(exam, dict) else exam.passed
        exam_type = exam.get("exam_type") if isinstance(exam, dict) else exam.exam_type
        attended = exam.get("attended") if isinstance(exam, dict) else exam.attended

        if not attended:
            return "referred_to_hr"
        if passed and exam_type == "baseline":
            return "eligible_for_offer"
        if passed and exam_type == "knowledge_check":
            return "deployment_ready"
        if score is not None and score < 40:
            return "recommended_loi_cancellation"
        if score is not None and score < 60:
            return "referred_to_hr"
        return None

    @staticmethod
    def _oid(value: str) -> ObjectId:
        try:
            return ObjectId(value)
        except Exception as exc:
            raise bad_request_exception("Invalid identifier") from exc
