from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from app.database import db
from app.schemas.file import FileCreate, FileResponse
from app.core.dependencies import get_current_user
from app.core.roles import ADMIN

router = APIRouter(prefix="/files", tags=["Files"])

@router.post("/", response_model=FileResponse)
def create_file(data: FileCreate, user=Depends(get_current_user)):
    if user["role"] != ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")

    result = db.files.insert_one(data.dict())
    return {
        "id": str(result.inserted_id),
        "filename": data.filename,
        "description": data.description
    }

@router.get("/", response_model=list[FileResponse])
def list_files(user=Depends(get_current_user)):
    return [
        {
            "id": str(f["_id"]),
            "filename": f["filename"],
            "description": f["description"]
        }
        for f in db.files.find()
    ]



