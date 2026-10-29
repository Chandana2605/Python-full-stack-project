from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import File, AccessRequest, User

router = APIRouter(tags=["User"])


@router.post("/request/{file_id}")
def request_access(
    file_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    req = AccessRequest(
        user_id=user.id,
        file_id=file_id,
        status="pending"
    )
    db.add(req)
    db.commit()
    return {"message": "Access request submitted"}

@router.get("/requests/my")
def my_requests(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return db.query(AccessRequest).filter(
        AccessRequest.user_id == user.id
    ).all()

# @router.get("/files/available")
# def available_files(
#     db: Session = Depends(get_db),
#     user=Depends(get_current_user)
# ):
#     approved_requests = db.query(AccessRequest).filter(
#         AccessRequest.user_id == user.id,
#         AccessRequest.status == "approved"
#     ).all()

#     file_ids = [req.file_id for req in approved_requests]

#     return db.query(File).filter(File.id.in_(file_ids)).all()
@router.delete("/requests/{request_id}")
def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    req = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.user_id == user.id
    ).first()

    if not req:
        raise HTTPException(404, "Request not found")

    db.delete(req)
    db.commit()
    return {"message": "Request cancelled"}

@router.get("/files")
def list_files(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    return db.query(File).all()
 
 
@router.get("/files/available")
def available_files(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
 
    approved_requests = db.query(AccessRequest).filter(
        AccessRequest.user_id == user.id,
        AccessRequest.status == "approved"
    ).all()
 
    if not approved_requests:
        return []
 
    file_ids = [req.file_id for req in approved_requests]
    files = db.query(File).filter(File.id.in_(file_ids)).all()
    return files