from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from app.database import db
from app.schemas.permission import PermissionResponse
from app.core.dependencies import get_current_user
from app.core.roles import ADMIN

router = APIRouter(prefix="/permissions", tags=["Permissions"])

@router.post("/approve/{request_id}", response_model=PermissionResponse)
def approve_request(request_id: str, user=Depends(get_current_user)):
    if user["role"] != ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")

    req = db.access_requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    db.permissions.insert_one({
        "user_id": req["user_id"],
        "file_id": req["file_id"]
    })

    return {
        "user_id": str(req["user_id"]),
        "file_id": str(req["file_id"])
    }
