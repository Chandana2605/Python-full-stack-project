from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from app.models import File
from app.dependencies import admin_only, get_db
from app.models import AccessRequest

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/requests")
def get_requests(
    db: Session = Depends(get_db),
    admin=Depends(admin_only)
):
    return db.query(AccessRequest).all()



@router.put("/requests/{request_id}/approve")
def approve_request(
    request_id: int,
    db: Session = Depends(get_db),
    admin=Depends(admin_only)
):
    req = db.query(AccessRequest).get(request_id)
    if not req:
        raise HTTPException(404, "Request not found")

    req.status = "approved"
    db.commit()
    return {"message": "Access approved"}

@router.put("/requests/{request_id}/reject")
def reject_request(
    request_id: int,
    db: Session = Depends(get_db),
    admin=Depends(admin_only)
):
    req = db.query(AccessRequest).get(request_id)
    if not req:
        raise HTTPException(404, "Request not found")

    req.status = "rejected"
    db.commit()
    return {"message": "Access rejected"}

@router.get("/permissions")
def permissions(
    db: Session = Depends(get_db),
    admin=Depends(admin_only)
):
    return db.query(AccessRequest).filter(
        AccessRequest.status == "approved"
    ).all()

@router.delete("/requests/{request_id}")
def delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    admin=Depends(admin_only)
):
    req = db.query(AccessRequest).get(request_id)
    if not req:
        raise HTTPException(404)

    db.delete(req)
    db.commit()
    return {"message": "Request deleted"}

@router.post("/files")
def create_file(
    name: str,
    description: str = "",
    db: Session = Depends(get_db),
    admin=Depends(admin_only)
):
   
    file = File(name=name, description=description)
    db.add(file)
    db.commit()
    return {"message": "File created"}
 
@router.put("/files/{file_id}")
def update_file(
    file_id: int,
    name: str = None,
    description: str = None,
    db: Session = Depends(get_db),
    admin=Depends(admin_only)
):

    file = db.query(File).get(file_id)
    if not file:
        raise HTTPException(404, "File not found")
    
    if name:
        file.name = name
    if description:
        file.description = description
    
    db.commit()
    return {"message": "File updated"}
 
@router.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    admin=Depends(admin_only)
):
   
    file = db.query(File).first()
    if not file:
        raise HTTPException(404, "File not found")
    
    db.delete(file)
    db.commit()
    return {"message": "File deleted"}

@router.get("/files")
def get_all_files(
    db: Session = Depends(get_db),
    admin=Depends(admin_only)
):
    
    files = db.query(File).all()
    return [
        {
            "id": file.id,
            "name": file.name,
            "description": file.description
        }
        for file in files
    ]