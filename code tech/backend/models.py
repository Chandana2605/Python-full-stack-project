from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    attempts: Mapped[List["Attempt"]] = relationship("Attempt", back_populates="user", cascade="all, delete-orphan")

class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # basic|intermediate|advanced
    concepts: Mapped[List["Concept"]] = relationship("Concept", back_populates="course", cascade="all, delete-orphan")

class Concept(Base):
    __tablename__ = "concepts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # basic|intermediate|advanced
    course: Mapped["Course"] = relationship("Course", back_populates="concepts")
    topics: Mapped[List["Topic"]] = relationship("Topic", back_populates="concept", cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    definition: Mapped[str] = mapped_column(Text)
    code_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    example: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)  # 1..3
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"))
    concept: Mapped["Concept"] = relationship("Concept", back_populates="topics")
    attempts: Mapped[List["Attempt"]] = relationship("Attempt", back_populates="topic", cascade="all, delete-orphan")

class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(String(50))       # typing/mcq/truefalse/flashcard/speed/fillblank
    clue_type: Mapped[str] = mapped_column(String(50))  # definition/code/example
    answer: Mapped[str] = mapped_column(Text)
    correct: Mapped[bool] = mapped_column(Boolean, default=False)
    score_awarded: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user: Mapped["User"] = relationship("User", back_populates="attempts")
    topic: Mapped["Topic"] = relationship("Topic", back_populates="attempts")
