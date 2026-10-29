from sqlalchemy import Column,Integer,String,DateTime,ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Registration(Base):
    __tablename__="registrations"
    id=Column(Integer,primary_key=True,index=True)
    attendee_name=Column(String,nullable=False)
    status=Column(String,nullable=False,default="Registered")
    user_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    event_id=Column(Integer,ForeignKey("events.id"),nullable=False)
    user=relationship("User")
    event=relationship("Event")
    created_at=Column(DateTime,default=datetime.utcnow)