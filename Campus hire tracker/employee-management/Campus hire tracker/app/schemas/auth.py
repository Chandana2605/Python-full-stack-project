from pydantic import BaseModel, EmailStr, Field

from app.core.enums import Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: EmailStr
    role: Role
    must_change_password: bool


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class CurrentUser(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: Role
    is_active: bool
    must_change_password: bool
