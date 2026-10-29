import asyncio

from app.core.enums import Role
from app.core.security import get_password_hash
from app.db.postgresql import close_postgresql_connection, connect_to_postgresql, get_database
from app.schemas.common import utc_now
from app.utils.ids import new_id


async def seed() -> None:
    await connect_to_postgresql()
    db = get_database()
    email = "manager@example.com"
    if not await db.users.find_one({"email": email}):
        now = utc_now()
        await db.users.insert_one(
            {
                "id": new_id(),
                "email": email,
                "name": "Default L&D Manager",
                "role": Role.LND_MANAGER.value,
                "hashed_password": get_password_hash("ChangeMe123!"),
                "must_change_password": True,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        )
        print("Created manager@example.com with temporary password ChangeMe123!")
    else:
        print("manager@example.com already exists")
    await close_postgresql_connection()


if __name__ == "__main__":
    asyncio.run(seed())
