from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password

def seed_admin():
    db=SessionLocal()
    try:
        admin=db.query(User).filter(User.role=="admin").first()
        if admin:
            return
        admin_user=User(
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin"
        )
        db.add(admin_user)
        db.commit()
    finally:
        db.close()