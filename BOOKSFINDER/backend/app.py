from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, date
from collections import Counter

from database import engine, get_db, Base
from models import User, Book, UserBook, Review, BookPage, ReadingSession
from schemas import (
    UserCreate, UserLogin, Token, UserOut, BookCreate, BookOut, 
    BookApproval, ReviewCreate, ReviewOut, UserBookCreate, UserBookUpdate, UserBookOut,
    BookPageOut, ReadingSessionCreate
)
from auth import (
    get_password_hash, authenticate_user, create_access_token, 
    update_login_streak, update_reading_streak, get_current_user, get_current_admin
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Book Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= INITIALIZE DEFAULT BOOKS =============
def init_default_books(db: Session):
    """Add default books with pages if database is empty"""
    existing = db.query(Book).filter(Book.is_default == True).first()
    if existing:
        return
    
    default_books = [
        {
            "title": "The Midnight Garden",
            "author_name": "Sarah Mitchell",
            "genre": "Fantasy",
            "category": "Fiction",
            "mood": "Magical",
            "description": "A young girl discovers a secret garden that only appears at midnight, where time moves differently and anything is possible.",
            "pages": [
                "Chapter 1: The Discovery\n\nLily had always been a curious child, but nothing could have prepared her for what she would find on that warm summer night. The old house had stood empty for decades, its garden wild and overgrown. As the clock struck midnight, she noticed something strange - the garden began to glow with an ethereal light.",
                "The wrought-iron gate, which had been rusted shut for years, now swung open easily at her touch. Beyond it lay a garden unlike anything she had ever seen. Flowers bloomed in impossible colors - blues that sparkled like sapphires, reds that glowed like embers, and purples that seemed to contain entire galaxies within their petals."
            ]
        },
        {
            "title": "Code Warriors",
            "author_name": "Alex Chen",
            "genre": "Science Fiction",
            "category": "Fiction",
            "mood": "Exciting",
            "description": "In a future where programmers are the ultimate warriors, one coder must save the digital world from collapse.",
            "pages": [
                "Chapter 1: System Breach\n\nThe alarm blared through the DataCenter at 3:47 AM. Maya's fingers flew across her keyboard, lines of code streaming across multiple monitors. Someone had breached the mainframe, and if she couldn't stop them in the next ten minutes, the entire global network would crash.",
                "She'd been the youngest master programmer at the academy, graduating at just 16. Now, five years later, she was humanity's last line of defense against digital chaos. The breach was unlike anything she'd seen before - elegant, sophisticated, almost... alive."
            ]
        },
        {
            "title": "Recipes for the Soul",
            "author_name": "Maria Rodriguez",
            "genre": "Self-Help",
            "category": "Non-Fiction",
            "mood": "Inspiring",
            "description": "A heartwarming collection of life lessons told through family recipes and cooking memories.",
            "pages": [
                "Introduction: The Kitchen Table\n\nMy grandmother used to say that every recipe tells a story, and every meal shared is a memory made. Growing up in her kitchen, I learned that cooking isn't just about following instructions - it's about pouring love into every dish, understanding that food nourishes more than just our bodies.",
                "The first recipe she taught me was her famous chicken soup. 'This isn't just soup,' she would say, stirring the pot with a wooden spoon worn smooth by decades of use. 'This is comfort. This is home. This is everything good in the world, in one bowl.'"
            ]
        }
    ]
    
    for book_data in default_books:
        pages = book_data.pop("pages")
        book = Book(
            **book_data,
            is_default=True,
            status="approved",
            total_pages=len(pages),
            average_rating=4.5,
            total_reviews=0
        )
        db.add(book)
        db.flush()
        
        for idx, content in enumerate(pages, 1):
            page = BookPage(book_id=book.id, page_number=idx, content=content)
            db.add(page)
    
    db.commit()

@app.on_event("startup")
async def startup_event():
    db = next(get_db())
    init_default_books(db)

# ============= AUTHENTICATION ENDPOINTS =============

@app.post("/token", response_model=Token)
def token_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    update_login_streak(db, user)
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
    update_login_streak(db, db_user)
    
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
    
    update_login_streak(db, user)
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
        title=book.title,
        author_name=book.author,
        genre=book.genre,
        category=book.category,
        mood=book.mood,
        description=book.description,
        is_default=True,
        status="approved",
        author_id=None,
        total_pages=len(book.pages) if book.pages else 0
    )
    db.add(db_book)
    db.flush()
    
    if book.pages:
        for idx, content in enumerate(book.pages, 1):
            page = BookPage(book_id=db_book.id, page_number=idx, content=content)
            db.add(page)
    
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
        title=book.title,
        author_name=book.author,
        genre=book.genre,
        category=book.category,
        mood=book.mood,
        description=book.description,
        author_id=current_user.id,
        status="pending",
        is_default=False,
        total_pages=len(book.pages) if book.pages else 0
    )
    db.add(db_book)
    db.flush()
    
    if book.pages:
        for idx, content in enumerate(book.pages, 1):
            page = BookPage(book_id=db_book.id, page_number=idx, content=content)
            db.add(page)
    
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
        (Book.status == "approved") | (Book.is_default == True)
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

@app.get("/books/{book_id}/pages", response_model=List[BookPageOut])
def get_book_pages(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    pages = db.query(BookPage).filter(BookPage.book_id == book_id).order_by(BookPage.page_number).all()
    return pages

@app.post("/books/{book_id}/read")
def record_reading_session(
    book_id: int,
    session: ReadingSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record that user read pages and update streak"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    today = date.today()
    existing_session = db.query(ReadingSession).filter(
        ReadingSession.user_id == current_user.id,
        ReadingSession.book_id == book_id,
        ReadingSession.session_date == today
    ).first()
    
    if existing_session:
        existing_session.pages_read += session.pages_read
    else:
        new_session = ReadingSession(
            user_id=current_user.id,
            book_id=book_id,
            pages_read=session.pages_read,
            session_date=today
        )
        db.add(new_session)
    
    update_reading_streak(db, current_user)
    
    user_book = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.book_id == book_id
    ).first()
    
    if user_book:
        user_book.current_page += session.pages_read
        if user_book.reading_status == "wish_to_read":
            user_book.reading_status = "currently_reading"
            user_book.started_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Reading session recorded",
        "streak": current_user.current_streak,
        "pages_read": session.pages_read
    }

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
        "current_page": db_user_book.current_page,
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
        "current_page": user_book.current_page,
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
            "current_page": ub.current_page,
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