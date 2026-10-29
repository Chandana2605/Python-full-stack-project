from fastapi import APIRouter, Depends, Query

from app.api.deps import require_roles
from app.core.enums import RequestStatus, Role
from app.schemas.auth import CurrentUser
from app.schemas.batches import BatchOut, CandidateOut, ChangeRequestOut
from app.services import batch_service, request_service

router = APIRouter()


@router.get("/assigned-program-batches", response_model=list[BatchOut], summary="View assigned program batches")
async def read_assigned_program_batches(
    user: CurrentUser = Depends(require_roles(Role.PROGRAM_MANAGER)),
) -> list[dict]:
    return await batch_service.list_batches_readonly(user.model_dump())


@router.get(
    "/assigned-program-batches/{batch_id}/candidates",
    response_model=list[CandidateOut],
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
    summary="View candidates in assigned program batch",
)
async def read_batch_candidates(
    batch_id: str,
    user: CurrentUser = Depends(require_roles(Role.PROGRAM_MANAGER)),
) -> list[dict]:
    batches = await batch_service.list_batches_readonly(user.model_dump())
    if not any(batch["id"] == batch_id for batch in batches):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Batch is not assigned to this program")
    return await batch_service.list_batch_candidates(batch_id)


@router.get(
    "/configuration/rule-change-requests",
    response_model=list[ChangeRequestOut],
    summary="View configuration rule change requests sent by L&D Manager",
)
async def read_rule_change_requests(
    status: RequestStatus | None = Query(default=None),
    user: CurrentUser = Depends(require_roles(Role.PROGRAM_MANAGER)),
) -> list[dict]:
    return await request_service.list_rule_change_requests(status)
