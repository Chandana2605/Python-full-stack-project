from sqlalchemy import Column, Integer, String, ForeignKey
from .database import Base
 
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)  # admin or user
 
class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
 
class AccessRequest(Base):
    __tablename__ = "access_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_id = Column(Integer, ForeignKey("files.id"))
    status = Column(String, default="pending")  # pending, approved, rejected