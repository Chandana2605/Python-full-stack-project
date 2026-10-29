from fastapi import HTTPException, status

from app.core.enums import Role, TimelineEventType
from app.core.security import get_password_hash
from app.db.postgresql import get_database
from app.schemas.common import utc_now
from app.schemas.users import UserCreate
from app.services.timeline_service import add_timeline_event
from app.utils.ids import new_id


async def create_user(payload: UserCreate, actor_id: str) -> dict:
    if payload.role == Role.LND_MANAGER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create L&D Manager here")
    db = get_database()
    existing = await db.users.find_one({"$or": [{"email": payload.email.lower()}, {"employee_id": payload.employee_id}]})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or employee ID already exists")
    now = utc_now()
    user = {
        "id": new_id(),
        "email": payload.email.lower(),
        "name": payload.name,
        "employee_id": payload.employee_id,
        "role": payload.role.value,
        "hashed_password": get_password_hash(payload.temporary_password),
        "must_change_password": True,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    await db.users.insert_one(user)
    await add_timeline_event(user["id"], actor_id, TimelineEventType.USER_CREATED, f"User {user['email']} created")
    user.pop("hashed_password", None)
    return user


async def list_users(role: Role | None = None) -> list[dict]:
    query = {"role": role.value} if role else {}
    users = await get_database().users.find(query).to_list(length=1000)
    for user in users:
        user.pop("hashed_password", None)
    return users


async def get_user(user_id: str) -> dict | None:
    user = await get_database().users.find_one({"id": user_id})
    if user:
        user.pop("hashed_password", None)
    return user
