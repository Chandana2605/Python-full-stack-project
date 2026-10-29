from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.enums import Role


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    employee_id: str = Field(min_length=1, max_length=50)
    role: Role
    temporary_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    employee_id: str | None = None
    role: Role
    is_active: bool
    must_change_password: bool
    created_at: datetime
