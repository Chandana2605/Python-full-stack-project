from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str

class FileResponse(BaseModel):
    id: int
    name: str
    description: str
