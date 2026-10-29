from sqlalchemy import Column,Integer,String,ForeignKey,DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Event(Base):
    __tablename__="events"
    id=Column(Integer,primary_key=True,index=True)
    event_name=Column(String,nullable=False)
    date=Column(DateTime,nullable=False)
    location=Column(String,nullable=False)
    created_by=Column(Integer,ForeignKey("users.id"),nullable=False)
    creator=relationship("User")
    created_at=Column(DateTime,default=datetime.utcnow)
