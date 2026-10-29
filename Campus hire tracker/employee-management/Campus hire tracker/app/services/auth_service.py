from fastapi import HTTPException, status

from app.core.security import create_access_token, create_refresh_token, decode_token, get_password_hash, verify_password
from app.db.postgresql import get_database
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshTokenRequest, TokenResponse
from app.schemas.common import utc_now


def _build_token_response(user: dict) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(subject=user["id"], role=user["role"]),
        refresh_token=create_refresh_token(subject=user["id"], role=user["role"]),
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        must_change_password=user["must_change_password"],
    )


async def login(payload: LoginRequest) -> TokenResponse:
    user = await get_database().users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return _build_token_response(user)


async def refresh_access_token(payload: RefreshTokenRequest) -> TokenResponse:
    try:
        token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = await get_database().users.find_one({"id": user_id})
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user")
    return _build_token_response(user)


async def change_password(user_id: str, payload: ChangePasswordRequest) -> dict[str, str]:
    db = get_database()
    user = await db.users.find_one({"id": user_id})
    if not user or not verify_password(payload.current_password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if verify_password(payload.new_password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "hashed_password": get_password_hash(payload.new_password),
                "must_change_password": False,
                "updated_at": utc_now(),
            }
        },
    )
    return {"message": "Password changed successfully"}
