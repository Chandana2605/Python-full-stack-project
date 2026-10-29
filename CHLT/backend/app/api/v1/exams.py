from fastapi import APIRouter, Depends, File, UploadFile, status

from .users import get_database, require_roles
from ...exceptions.http_exceptions import bad_request_exception, forbidden_exception, not_found_exception
from ...models.exam import ExamCreate, ExamOut, ExamUpdate
from ...services.exam_service import ExamService
from ...utils.excel_parser import parse_excel_file

router = APIRouter(prefix="/exams", tags=["Exams"])


def get_exam_service() -> ExamService:
    return ExamService(get_database())


async def _assert_batch_owner_access(batch_id: str | None, current_user: dict) -> None:
    if current_user["role"] != "batch_owner" or not batch_id:
        return
    batch = await get_database().batches.find_one({"_id": get_exam_service()._oid(batch_id)})
    if not batch or batch.get("owner_id") != current_user["id"]:
        raise forbidden_exception("You can only manage exams for your assigned batches")


@router.post("", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
async def create_exam(
    payload: ExamCreate,
    current_user: dict = Depends(require_roles("admin", "batch_owner")),
    service: ExamService = Depends(get_exam_service),
) -> ExamOut:
    return await service.create_exam(payload, current_user)


@router.get("", response_model=list[ExamOut])
async def list_exams(
    exam_type: str | None = None,
    current_user: dict = Depends(require_roles("admin", "batch_owner", "program_manager")),
    service: ExamService = Depends(get_exam_service),
) -> list[ExamOut]:
    return await service.list_exams(current_user, exam_type)


@router.patch("/{exam_id}", response_model=ExamOut)
async def update_exam(
    exam_id: str,
    payload: ExamUpdate,
    current_user: dict = Depends(require_roles("admin", "batch_owner")),
    service: ExamService = Depends(get_exam_service),
) -> ExamOut:
    return await service.update_exam(exam_id, payload, current_user)


@router.post("/baseline/upload", response_model=list[ExamOut])
async def upload_baseline_scores(
    batch_id: str | None = None,
    current_user: dict = Depends(require_roles("admin", "batch_owner")),
    file: UploadFile = File(...),
) -> list[ExamOut]:
    await _assert_batch_owner_access(batch_id, current_user)
    records = parse_excel_file(await file.read(), ["candidate_email", "score", "attended", "passed"])
    db = get_database()
    service = get_exam_service()
    created: list[ExamOut] = []

    for row in records:
        candidate = await db.candidates.find_one({"email": row["candidate_email"].lower()})
        if not candidate:
            raise not_found_exception(f"Candidate not found for email {row['candidate_email']}")
        payload = ExamCreate(
            candidate_id=str(candidate["_id"]),
            exam_type="baseline",
            coding_name=None,
            score=float(row["score"]) if row["score"] is not None else None,
            attended=bool(row["attended"]),
            passed=bool(row["passed"]),
            attempt_number=1,
            status="passed" if bool(row["passed"]) else ("not_attended" if not bool(row["attended"]) else "failed"),
            batch_id=batch_id or candidate.get("batch_id"),
        )
        created.append(await service.create_exam(payload, current_user))

    return created


@router.post("/knowledge-check/upload", response_model=list[ExamOut])
async def upload_knowledge_check_scores(
    coding_name: str,
    batch_id: str | None = None,
    current_user: dict = Depends(require_roles("admin", "batch_owner")),
    file: UploadFile = File(...),
) -> list[ExamOut]:
    await _assert_batch_owner_access(batch_id, current_user)
    records = parse_excel_file(await file.read(), ["candidate_email", "score", "attended", "passed", "attempt_number"])
    db = get_database()
    service = get_exam_service()
    created: list[ExamOut] = []

    for row in records:
        candidate = await db.candidates.find_one({"email": row["candidate_email"].lower()})
        if not candidate:
            raise not_found_exception(f"Candidate not found for email {row['candidate_email']}")
        payload = ExamCreate(
            candidate_id=str(candidate["_id"]),
            exam_type="knowledge_check",
            coding_name=coding_name,
            score=float(row["score"]) if row["score"] is not None else None,
            attended=bool(row["attended"]),
            passed=bool(row["passed"]),
            attempt_number=int(row["attempt_number"]),
            status="passed" if bool(row["passed"]) else ("not_attended" if not bool(row["attended"]) else "failed"),
            batch_id=batch_id or candidate.get("batch_id"),
        )
        created.append(await service.create_exam(payload, current_user))

    return created
