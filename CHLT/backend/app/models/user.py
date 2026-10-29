from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


RoleName = Literal["admin", "batch_owner", "program_manager"]


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    employee_id: str = Field(..., min_length=3, max_length=50)
    role: RoleName


class UserCreate(UserBase):
    temporary_password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    role: RoleName | None = None
    is_active: bool | None = None


class UserOut(UserBase):
    id: str
    force_password_change: bool
    is_active: bool
    invitation_email_sent: bool | None = None
    invitation_sent_at: datetime | None = None
    invitation_last_attempt_at: datetime | None = None
    invitation_last_error: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleName
    must_change_password: bool
    user: UserOut


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class UserProvisionResponse(BaseModel):
    user: UserOut
    invitation_email_sent: bool
    invitation_message: str


class ResendInvitationRequest(BaseModel):
    temporary_password: str = Field(..., min_length=8, max_length=128)


class EmailConnectionTestRequest(BaseModel):
    recipient_email: EmailStr


class EmailConnectionTestResponse(BaseModel):
    connection_ok: bool
    email_sent: bool
    message: str
