from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..core.config import get_settings
from ..core.security import get_password_hash

client: AsyncIOMotorClient | None = None
database: AsyncIOMotorDatabase | None = None


def get_database() -> AsyncIOMotorDatabase:
    if database is None:
        raise RuntimeError("Database is not initialized")
    return database


async def connect_to_mongo() -> None:
    global client, database
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    database = client[settings.mongodb_db_name]

    await _ensure_indexes()
    await _seed_roles()
    await _seed_admin_user()


async def close_mongo_connection() -> None:
    global client, database
    if client:
        client.close()
    client = None
    database = None


async def _ensure_indexes() -> None:
    db = get_database()
    await db.users.create_index("email", unique=True)
    await db.users.create_index("employee_id", unique=True)
    await db.roles.create_index("name", unique=True)
    await db.candidates.create_index([("year", 1), ("email", 1)], unique=True)
    await db.candidates.create_index("batch_id")
    await db.batches.create_index([("year", 1), ("phase", 1), ("name", 1)], unique=True)
    await db.exams.create_index([("candidate_id", 1), ("exam_type", 1), ("attempt_number", 1)], unique=True)
    await db.approvals.create_index("status")
    await db.dropouts.create_index([("candidate_id", 1), ("is_active", 1)])
    await db.audit_logs.create_index([("entity_type", 1), ("entity_id", 1), ("created_at", -1)])


async def _seed_roles() -> None:
    db = get_database()
    for role in [
        {"name": "admin", "description": "L&D Manager with full access"},
        {"name": "batch_owner", "description": "Assigned-batch operational role"},
        {"name": "program_manager", "description": "Read-only governance role"},
    ]:
        await db.roles.update_one({"name": role["name"]}, {"$setOnInsert": role}, upsert=True)


async def _seed_admin_user() -> None:
    db = get_database()
    settings = get_settings()

    now = datetime.now(timezone.utc)
    seed_document = {
        "name": settings.admin_name,
        "email": settings.admin_email.lower(),
        "employee_id": settings.admin_employee_id,
        "role": "admin",
        "password_hash": get_password_hash(settings.admin_temporary_password),
        "force_password_change": True,
        "is_active": True,
        "created_by": None,
        "updated_at": now,
    }
    existing = await db.users.find_one(
        {
            "$or": [
                {"email": settings.admin_email.lower()},
                {"employee_id": settings.admin_employee_id},
                {"role": "admin"},
            ]
        }
    )
    if existing:
        await db.users.update_one(
            {"_id": existing["_id"]},
            {"$set": seed_document, "$setOnInsert": {"created_at": now}},
        )
        return

    seed_document["created_at"] = now
    await db.users.insert_one(seed_document)
