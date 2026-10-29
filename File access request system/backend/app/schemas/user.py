from pydantic import BaseModel

# Used for signup & login input
class UserCreate(BaseModel):
    username: str
    password: str

# Used for returning user info (SAFE – no password)
class UserResponse(BaseModel):
    id: str
    username: str
    role: str
