from sqlalchemy import Boolean, Column, Integer, String, Float, ForeignKey, DateTime, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    current_streak = Column(Integer, default=0)
    last_login_date = Column(Date, nullable=True)
    last_read_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    posted_books = relationship("Book", back_populates="author", foreign_keys="Book.author_id")
    user_books = relationship("UserBook", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    reading_sessions = relationship("ReadingSession", back_populates="user", cascade="all, delete-orphan")

class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    author_name = Column(String, nullable=False)
    genre = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False)
    mood = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    cover_image = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)
    status = Column(String, default="pending", nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    average_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    total_pages = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    author = relationship("User", back_populates="posted_books", foreign_keys=[author_id])
    user_books = relationship("UserBook", back_populates="book", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="book", cascade="all, delete-orphan")
    pages = relationship("BookPage", back_populates="book", cascade="all, delete-orphan")
    reading_sessions = relationship("ReadingSession", back_populates="book", cascade="all, delete-orphan")

class BookPage(Base):
    __tablename__ = "book_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    
    book = relationship("Book", back_populates="pages")

class UserBook(Base):
    __tablename__ = "user_books"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    reading_status = Column(String, default="wish_to_read")
    is_favorite = Column(Boolean, default=False)
    current_page = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="user_books")
    book = relationship("Book", back_populates="user_books")

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    rating = Column(Float, nullable=False)
    review_text = Column(Text, nullable=True)
    is_recommended = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="reviews")
    book = relationship("Book", back_populates="reviews")

class ReadingSession(Base):
    __tablename__ = "reading_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    pages_read = Column(Integer, default=0)
    session_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="reading_sessions")
    book = relationship("Book", back_populates="reading_sessions")