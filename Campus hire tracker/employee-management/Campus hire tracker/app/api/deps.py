from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.enums import Role
from app.core.security import decode_token
from app.db.postgresql import get_database
from app.schemas.auth import CurrentUser
from app.schemas.common import utc_now

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/swagger-token")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await get_database().users.find_one({"id": user_id})
    if not user or not user.get("is_active", False):

        
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user")
    return CurrentUser(**user)


async def get_current_ready_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required before accessing this resource",
        )
    return user


def require_roles(*roles: Role) -> Callable:
    async def checker(user: CurrentUser = Depends(get_current_ready_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker
