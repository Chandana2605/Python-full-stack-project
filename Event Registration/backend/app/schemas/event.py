from pydantic import BaseModel
from datetime import datetime

class EventCreate(BaseModel):
    event_name: str
    date: datetime
    location: str

class EventResponse(BaseModel):
    id: int
    event_name: str
    date: datetime
    location: str
    created_at: datetime
    
    class Config:
        from_attributes=True

