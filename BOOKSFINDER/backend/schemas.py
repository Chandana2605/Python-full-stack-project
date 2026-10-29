from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    role: str
    current_streak: int
    
    class Config:
        from_attributes = True

class BookPageCreate(BaseModel):
    content: str

class BookCreate(BaseModel):
    title: str
    author: str  # This will map to author_name in the database
    genre: str
    category: str
    mood: Optional[str] = None
    description: Optional[str] = None
    pages: Optional[List[str]] = []

class BookOut(BaseModel):
    id: int
    title: str
    author_name: str  # FIXED: Changed to match database column name
    genre: str
    category: str
    mood: Optional[str] = None
    description: Optional[str] = None
    is_default: bool
    status: str
    author_id: Optional[int] = None
    rejection_reason: Optional[str] = None
    average_rating: float
    total_reviews: int
    total_pages: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookPageOut(BaseModel):
    id: int
    book_id: int
    page_number: int
    content: str
    
    class Config:
        from_attributes = True

class BookApproval(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None

class ReviewCreate(BaseModel):
    rating: float = Field(..., ge=0, le=5)
    review_text: Optional[str] = None
    is_recommended: bool = True

class ReviewOut(BaseModel):
    id: int
    user_id: int
    book_id: int
    rating: float
    review_text: Optional[str]
    is_recommended: bool
    created_at: datetime
    username: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserBookCreate(BaseModel):
    book_id: int
    reading_status: str

class UserBookUpdate(BaseModel):
    reading_status: Optional[str] = None
    is_favorite: Optional[bool] = None

class UserBookOut(BaseModel):
    id: int
    book_id: int
    reading_status: str
    is_favorite: bool
    current_page: int
    book: Optional[BookOut] = None
    
    class Config:
        from_attributes = True

class ReadingSessionCreate(BaseModel):
    pages_read: int = Field(..., ge=1)