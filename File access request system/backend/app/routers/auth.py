from fastapi import APIRouter, HTTPException
from app.database import db
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import TokenResponse
from app.models.user import user_document
from app.core.security import hash_password, verify_password, create_access_token
from app.core.roles import USER

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=UserResponse)
def signup(data: UserCreate):
    if db.users.find_one({"username": data.username}):
        raise HTTPException(status_code=400, detail="User already exists")

    result = db.users.insert_one(
        user_document(
            data.username,
            hash_password(data.password),
            USER
        )
    )

    return {
        "id": str(result.inserted_id),
        "username": data.username,
        "role": USER
    }

@router.post("/login", response_model=TokenResponse)
def login(data: UserCreate):
    user = db.users.find_one({"username": data.username})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": str(user["_id"]),
        "role": user["role"]
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }

