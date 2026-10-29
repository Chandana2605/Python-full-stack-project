from fastapi import Depends
from sqlalchemy.orm import Session
from .database import get_db
from .auth import get_current_user, get_current_admin
from .models import User

async def get_db_session(db: Session = Depends(get_db)):
    return db

async def get_user(current_user: User = Depends(get_current_user)):
    return current_user

async def get_admin(current_admin: User = Depends(get_current_admin)):
    return current_admin