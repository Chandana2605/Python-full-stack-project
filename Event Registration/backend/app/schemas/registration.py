from pydantic import BaseModel
from datetime import datetime

class RegistrationCreate(BaseModel):
    event_id: int
    attendee_name: str

class RegistrationResponse(BaseModel):
    id: int
    attendee_name: str
    status: str
    event_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes=True
