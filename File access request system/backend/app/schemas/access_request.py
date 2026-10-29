from pydantic import BaseModel

# User requests access
class AccessRequestCreate(BaseModel):
    file_id: str

# Admin / UI sees requests
class AccessRequestResponse(BaseModel):
    id: str
    user_id: str
    file_id: str
    status: str
