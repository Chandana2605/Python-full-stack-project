from pydantic import BaseModel

class PermissionResponse(BaseModel):
    user_id: str
    file_id: str
