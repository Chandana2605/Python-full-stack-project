from typing import Annotated

from bson import ObjectId
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from ...core.security import decode_token
from ...db.mongo import get_database
from ...exceptions.http_exceptions import bad_request_exception, forbidden_exception, unauthorized_exception
from ...services.auth_service import AuthService
from ...services.user_service import UserService, serialize_document

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_user_service() -> UserService:
    return UserService(get_database())


def get_auth_service() -> AuthService:
    return AuthService(get_database())


def to_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as exc:
        raise bad_request_exception("Invalid identifier") from exc


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    try:
        payload = decode_token(token)
        user_id = payload["sub"]
    except (JWTError, KeyError) as exc:
        raise unauthorized_exception("Invalid or expired token") from exc

    user = await get_database().users.find_one({"_id": ObjectId(user_id)})
    if not user or not user.get("is_active", True):
        raise unauthorized_exception("User is inactive or missing")
    return serialize_document(user)


def require_roles(*roles: str):
    async def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in roles:
            raise forbidden_exception("You do not have permission to access this resource")
        return current_user

    return dependency


async def enforce_candidate_access(candidate: dict, current_user: dict) -> None:
    if current_user["role"] in {"admin", "program_manager"}:
        return
    batch_id = candidate.get("batch_id")
    if not batch_id:
        raise forbidden_exception("Candidate is not assigned to your batch")
    batch = await get_database().batches.find_one({"_id": to_object_id(batch_id)})
    if not batch or batch.get("owner_id") != current_user["id"]:
        raise forbidden_exception("Candidate is outside your assigned batches")


async def enforce_batch_owner_access(batch_id: str | None, current_user: dict) -> None:
    if current_user["role"] != "batch_owner" or not batch_id:
        return
    batch = await get_database().batches.find_one({"_id": to_object_id(batch_id)})
    if not batch or batch.get("owner_id") != current_user["id"]:
        raise forbidden_exception("You can only access your assigned batches")
