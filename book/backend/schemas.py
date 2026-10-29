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

class BookCreate(BaseModel):
    title: str
    author_name: str
    genre: str
    category: str
    mood: Optional[str] = None
    description: Optional[str] = None

class BookOut(BaseModel):
    id: int
    title: str
    author_name: str
    genre: str
    category: str
    mood: Optional[str]
    description: Optional[str]
    is_default: bool
    status: str
    author_id: Optional[int]
    rejection_reason: Optional[str]
    average_rating: float
    total_reviews: int
    created_at: datetime
    
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
    book: Optional[BookOut] = None
    
    class Config:
        from_attributes = True