from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.postgresql import close_postgresql_connection, connect_to_postgresql


app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    await connect_to_postgresql()


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_postgresql_connection()


app.include_router(api_router, prefix="/api/v1")
