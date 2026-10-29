from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.v1.admin import router as admin_router
from .api.v1.auth import router as auth_router
from .api.v1.batch_owner import router as batch_owner_router
from .api.v1.program_manager import router as program_manager_router
from .core.config import get_settings
from .db.mongo import close_mongo_connection, connect_to_mongo

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)
app.include_router(batch_owner_router, prefix=settings.api_v1_prefix)
app.include_router(program_manager_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": settings.app_name}
