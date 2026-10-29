from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate,UserLogin,TokenResponse
from app.core.security import hash_password,verify_password,create_access_token

router=APIRouter(prefix="/auth",tags=["auth"])

@router.post("/signup",status_code=status.HTTP_201_CREATED)
def signup(
    user_in:UserCreate,
    db: Session=Depends(get_db)
):
    existing_user=db.query(User).filter(
        User.username==user_in.username
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )
    new_user=User(
        username=user_in.username,
        password_hash=hash_password(user_in.password),
        role="user"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return{
        "id":new_user.id,
        "username":new_user.username,
        "role":new_user.role
    }
    
@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.username == form_data.username
    ).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "role": user.role
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username
    }
