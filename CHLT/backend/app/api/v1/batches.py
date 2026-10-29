from fastapi import APIRouter, Depends, status

from .users import get_current_user, get_database, require_roles
from ...models.batch import BatchAssignCandidatesRequest, BatchCreate, BatchOut, BatchUpdate
from ...services.batch_service import BatchService

router = APIRouter(prefix="/batches", tags=["Batches"])


def get_batch_service() -> BatchService:
    return BatchService(get_database())


@router.post("", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: BatchCreate,
    current_user: dict = Depends(require_roles("admin")),
    service: BatchService = Depends(get_batch_service),
) -> BatchOut:
    return await service.create_batch(payload, current_user["id"])


@router.get("", response_model=list[BatchOut])
async def list_batches(
    current_user: dict = Depends(require_roles("admin", "batch_owner", "program_manager")),
    service: BatchService = Depends(get_batch_service),
) -> list[BatchOut]:
    return await service.list_batches(current_user)


@router.patch("/{batch_id}", response_model=BatchOut)
async def update_batch(
    batch_id: str,
    payload: BatchUpdate,
    current_user: dict = Depends(require_roles("admin", "batch_owner")),
    service: BatchService = Depends(get_batch_service),
) -> BatchOut:
    return await service.update_batch(batch_id, payload, current_user)


@router.post("/{batch_id}/assign-candidates")
async def assign_candidates(
    batch_id: str,
    payload: BatchAssignCandidatesRequest,
    current_user: dict = Depends(require_roles("admin", "batch_owner")),
    service: BatchService = Depends(get_batch_service),
) -> dict:
    return await service.assign_candidates(batch_id, payload.candidate_ids, current_user)


@router.get("/{batch_id}/export")
async def export_batch_candidates(
    batch_id: str,
    current_user: dict = Depends(require_roles("admin", "batch_owner", "program_manager")),
    service: BatchService = Depends(get_batch_service),
) -> list[dict]:
    return await service.export_batch_candidates(batch_id, current_user)
