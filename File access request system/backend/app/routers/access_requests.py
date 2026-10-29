from fastapi import APIRouter, Depends
from bson import ObjectId
from app.database import db
from app.schemas.access_request import AccessRequestCreate, AccessRequestResponse
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/access-requests", tags=["Access Requests"])

@router.post("/", response_model=AccessRequestResponse)
def request_access(data: AccessRequestCreate, user=Depends(get_current_user)):
    result = db.access_requests.insert_one({
        "user_id": ObjectId(user["id"]),
        "file_id": ObjectId(data.file_id),
        "status": "pending"
    })

    return {
        "id": str(result.inserted_id),
        "user_id": user["id"],
        "file_id": data.file_id,
        "status": "pending"
    }
