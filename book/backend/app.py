from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime
from collections import Counter

from database import engine, get_db, Base
from models import User, Book, UserBook, Review
from schemas import (
    UserCreate, UserLogin, Token, UserOut, BookCreate, BookOut, 
    BookApproval, ReviewCreate, ReviewOut, UserBookCreate, UserBookUpdate, UserBookOut
)
from auth import (
    get_password_hash, authenticate_user, create_access_token, 
    update_user_streak, get_current_user, get_current_admin
)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Book Finder API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= AUTHENTICATION ENDPOINTS =============

@app.post("/token", response_model=Token)
def token_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 compatible token login for Swagger UI"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    update_user_streak(db, user)
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username
    }

@app.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=get_password_hash(user.password),
        role="user"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    update_user_streak(db, db_user)
    
    access_token = create_access_token(data={"sub": db_user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": db_user.role,
        "username": db_user.username
    }

@app.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    update_user_streak(db, user)
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username
    }

@app.post("/admin/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def admin_signup(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.role == "admin").first():
        raise HTTPException(status_code=400, detail="Admin already exists")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=get_password_hash(user.password),
        role="admin"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    access_token = create_access_token(data={"sub": db_user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": db_user.role,
        "username": db_user.username
    }

@app.post("/admin/login", response_model=Token)
def admin_login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, credentials.email, credentials.password)
    if not user or user.role != "admin":
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username
    }

# ============= ADMIN ENDPOINTS =============

@app.get("/admin/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    users = db.query(User).filter(User.role == "user").all()
    user_data = [{"username": u.username, "streak": u.current_streak} for u in users]
    
    pending_books = db.query(Book).filter(Book.status == "pending").count()
    approved_books = db.query(Book).filter(Book.status == "approved").count()
    rejected_books = db.query(Book).filter(Book.status == "rejected").count()
    
    return {
        "total_users": len(users),
        "users": user_data,
        "pending_books": pending_books,
        "approved_books": approved_books,
        "rejected_books": rejected_books
    }

@app.post("/admin/books", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def admin_add_default_book(
    book: BookCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    db_book = Book(
        **book.dict(),
        is_default=True,
        status="approved",
        author_id=None
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@app.delete("/admin/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return None

@app.get("/admin/books/pending", response_model=List[BookOut])
def get_pending_books(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return db.query(Book).filter(Book.status == "pending").all()

@app.post("/admin/books/{book_id}/approve")
def approve_reject_book(
    book_id: int,
    approval: BookApproval,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if approval.approved:
        book.status = "approved"
        book.rejection_reason = None
    else:
        if not approval.rejection_reason:
            raise HTTPException(status_code=400, detail="Rejection reason required")
        book.status = "rejected"
        book.rejection_reason = approval.rejection_reason
    
    db.commit()
    db.refresh(book)
    return {"message": "Book status updated", "book": book}

@app.get("/admin/books/all", response_model=List[BookOut])
def get_all_books_admin(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return db.query(Book).all()

@app.get("/admin/books/{book_id}/reviews", response_model=List[ReviewOut])
def get_book_reviews_admin(
    book_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    reviews = db.query(Review).filter(Review.book_id == book_id).all()
    result = []
    for review in reviews:
        user = db.query(User).filter(User.id == review.user_id).first()
        review_dict = {
            "id": review.id,
            "user_id": review.user_id,
            "book_id": review.book_id,
            "rating": review.rating,
            "review_text": review.review_text,
            "is_recommended": review.is_recommended,
            "created_at": review.created_at,
            "username": user.username if user else "Unknown"
        }
        result.append(review_dict)
    return result

# ============= USER BOOK ENDPOINTS =============

@app.post("/books", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    book: BookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_book = Book(
        **book.dict(),
        author_id=current_user.id,
        status="pending",
        is_default=False
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@app.get("/books", response_model=List[BookOut])
def get_books(
    genre: Optional[str] = None,
    mood: Optional[str] = None,
    category: Optional[str] = None,
    min_rating: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Book).filter(
        (Book.status == "approved") | ((Book.is_default == True))
    )
    
    if genre:
        query = query.filter(Book.genre.ilike(f"%{genre}%"))
    if mood:
        query = query.filter(Book.mood.ilike(f"%{mood}%"))
    if category:
        query = query.filter(Book.category.ilike(f"%{category}%"))
    if min_rating:
        query = query.filter(Book.average_rating >= min_rating)
    
    return query.all()

@app.get("/books/{book_id}", response_model=BookOut)
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.post("/user-books", response_model=UserBookOut, status_code=status.HTTP_201_CREATED)
def add_book_to_user_list(
    user_book: UserBookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.book_id == user_book.book_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Book already in your list")
    
    db_user_book = UserBook(
        user_id=current_user.id,
        book_id=user_book.book_id,
        reading_status=user_book.reading_status,
        started_at=datetime.utcnow() if user_book.reading_status == "currently_reading" else None
    )
    db.add(db_user_book)
    db.commit()
    db.refresh(db_user_book)
    
    book = db.query(Book).filter(Book.id == user_book.book_id).first()
    return {
        "id": db_user_book.id,
        "book_id": db_user_book.book_id,
        "reading_status": db_user_book.reading_status,
        "is_favorite": db_user_book.is_favorite,
        "book": book
    }

@app.put("/user-books/{user_book_id}", response_model=UserBookOut)
def update_user_book(
    user_book_id: int,
    update_data: UserBookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_book = db.query(UserBook).filter(
        UserBook.id == user_book_id,
        UserBook.user_id == current_user.id
    ).first()
    
    if not user_book:
        raise HTTPException(status_code=404, detail="User book not found")
    
    if update_data.reading_status:
        user_book.reading_status = update_data.reading_status
        if update_data.reading_status == "currently_reading" and not user_book.started_at:
            user_book.started_at = datetime.utcnow()
        elif update_data.reading_status == "completed":
            user_book.completed_at = datetime.utcnow()
    
    if update_data.is_favorite is not None:
        user_book.is_favorite = update_data.is_favorite
    
    db.commit()
    db.refresh(user_book)
    
    book = db.query(Book).filter(Book.id == user_book.book_id).first()
    return {
        "id": user_book.id,
        "book_id": user_book.book_id,
        "reading_status": user_book.reading_status,
        "is_favorite": user_book.is_favorite,
        "book": book
    }

@app.get("/user-books", response_model=List[UserBookOut])
def get_user_books(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_books = db.query(UserBook).filter(UserBook.user_id == current_user.id).all()
    result = []
    for ub in user_books:
        book = db.query(Book).filter(Book.id == ub.book_id).first()
        result.append({
            "id": ub.id,
            "book_id": ub.book_id,
            "reading_status": ub.reading_status,
            "is_favorite": ub.is_favorite,
            "book": book
        })
    return result

# ============= REVIEW ENDPOINTS =============

@app.post("/books/{book_id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    book_id: int,
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.book_id == book_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this book")
    
    db_review = Review(
        user_id=current_user.id,
        book_id=book_id,
        rating=review.rating,
        review_text=review.review_text,
        is_recommended=review.is_recommended
    )
    db.add(db_review)
    
    # Update book average rating
    book = db.query(Book).filter(Book.id == book_id).first()
    if book:
        all_reviews = db.query(Review).filter(Review.book_id == book_id).all()
        total_rating = sum([r.rating for r in all_reviews]) + review.rating
        book.total_reviews = len(all_reviews) + 1
        book.average_rating = total_rating / book.total_reviews
    
    db.commit()
    db.refresh(db_review)
    
    return {
        "id": db_review.id,
        "user_id": db_review.user_id,
        "book_id": db_review.book_id,
        "rating": db_review.rating,
        "review_text": db_review.review_text,
        "is_recommended": db_review.is_recommended,
        "created_at": db_review.created_at,
        "username": current_user.username
    }

@app.get("/books/{book_id}/reviews", response_model=List[ReviewOut])
def get_book_reviews(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    reviews = db.query(Review).filter(Review.book_id == book_id).all()
    result = []
    for review in reviews:
        user = db.query(User).filter(User.id == review.user_id).first()
        result.append({
            "id": review.id,
            "user_id": review.user_id,
            "book_id": review.book_id,
            "rating": review.rating,
            "review_text": review.review_text,
            "is_recommended": review.is_recommended,
            "created_at": review.created_at,
            "username": user.username if user else "Unknown"
        })
    return result

# ============= USER DASHBOARD =============

@app.get("/dashboard")
def user_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_books = db.query(UserBook).filter(UserBook.user_id == current_user.id).all()
    
    favorites = []
    currently_reading = []
    completed = []
    wish_to_read = []
    
    for ub in user_books:
        book = db.query(Book).filter(Book.id == ub.book_id).first()
        if book:
            if ub.is_favorite:
                favorites.append(book)
            if ub.reading_status == "currently_reading":
                currently_reading.append(book)
            elif ub.reading_status == "completed":
                completed.append(book)
            elif ub.reading_status == "wish_to_read":
                wish_to_read.append(book)
    
    posted_books = db.query(Book).filter(Book.author_id == current_user.id).all()
    
    # Favorite genre
    completed_genres = [b.genre for b in completed]
    favorite_genre = None
    if completed_genres:
        genre_counts = Counter(completed_genres)
        favorite_genre = genre_counts.most_common(1)[0][0]
    
    return {
        "username": current_user.username,
        "streak": current_user.current_streak,
        "favorites": favorites,
        "currently_reading": currently_reading,
        "completed": completed,
        "wish_to_read": wish_to_read,
        "posted_books": posted_books,
        "favorite_genre": favorite_genre
    }

@app.get("/")
def root():
    return {"message": "Book Finder API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)