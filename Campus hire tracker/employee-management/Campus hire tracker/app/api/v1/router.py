from fastapi import APIRouter

from app.api.v1.routes import auth, batch_owner, manager, program_manager

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(batch_owner.router, prefix="/batch-owner", tags=["Batch Owner Workflows"])
api_router.include_router(manager.router, prefix="/lnd-manager", tags=["L&D Manager Administration"])
api_router.include_router(program_manager.router, prefix="/program-manager", tags=["Program Manager Read Only"])
