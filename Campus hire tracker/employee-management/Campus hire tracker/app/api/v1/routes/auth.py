from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_current_user
from app.schemas.auth import ChangePasswordRequest, CurrentUser, LoginRequest, RefreshTokenRequest, TokenResponse
from app.services.auth_service import change_password, login, refresh_access_token

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    description="Role-agnostic login. Send only email and password; the backend reads the role from PostgreSQL and returns it in the response.",
)
async def login_user(payload: LoginRequest) -> TokenResponse:
    return await login(payload)


@router.post("/swagger-token", response_model=TokenResponse, include_in_schema=False)
async def swagger_login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    return await login(LoginRequest(email=form.username, password=form.password))


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(payload: RefreshTokenRequest) -> TokenResponse:
    return await refresh_access_token(payload)


@router.post("/change-password", summary="Change temporary or current password")
async def change_user_password(
    payload: ChangePasswordRequest, user: CurrentUser = Depends(get_current_user)
) -> dict[str, str]:
    return await change_password(user.id, payload)
