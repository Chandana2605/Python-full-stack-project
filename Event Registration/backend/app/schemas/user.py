from pydantic import BaseModel

class UserCreate(BaseModel):
    username:str
    password:str

class UserLogin(BaseModel):
    username:str
    password:str

class TokenResponse(BaseModel):
    access_token:str
    token_type:str
    role:str
    username:str

class UserResponse(BaseModel):
    id:int
    username: str
    role:str

    class Config:
        from_attributes=True

