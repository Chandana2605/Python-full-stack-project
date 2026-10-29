from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from .deps import get_auth_service, get_current_user
from ...models.user import LoginResponse, PasswordChangeRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service=Depends(get_auth_service),
) -> LoginResponse:
    return await service.login(form_data.username, form_data.password)


@router.post("/change-password")
async def change_password(
    payload: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
    service=Depends(get_auth_service),
) -> dict:
    return await service.change_password(current_user["id"], payload)
