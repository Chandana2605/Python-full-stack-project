from database import SessionLocal
from models import Book, BookPage, User
from auth import get_password_hash

def seed():
    db = SessionLocal()
    try:
        # Ensure one admin exists (if not already)
        admin = db.query(User).filter(User.is_admin == True).first()
        if not admin:
            admin = User(
                name="Admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                is_admin=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print("Admin created: admin@example.com / admin123")

        # Default books
        if db.query(Book).filter(Book.is_default == True).count() == 0:
            b1 = Book(title="The Uplift Tale", author="A. Writer", genre="Fiction", mood="Uplifting",
                      category="Novel", is_default=True, status="approved", created_by_admin_id=admin.id)
            b2 = Book(title="Dark Depths", author="B. Author", genre="Horror", mood="Dark",
                      category="Novel", is_default=True, status="approved", created_by_admin_id=admin.id)
            db.add_all([b1, b2])
            db.commit()
            db.refresh(b1)
            db.refresh(b2)

            # Pages (ensure at least 2)
            pages_b1 = [
                BookPage(book_id=b1.id, page_number=1, content="Page 1: Beginning of The Uplift Tale."),
                BookPage(book_id=b1.id, page_number=2, content="Page 2: The journey starts."),
                BookPage(book_id=b1.id, page_number=3, content="Page 3: Hope and courage.")
            ]
            pages_b2 = [
                BookPage(book_id=b2.id, page_number=1, content="Page 1: Shadows gather."),
                BookPage(book_id=b2.id, page_number=2, content="Page 2: A whisper in the dark.")
            ]
            db.add_all(pages_b1 + pages_b2)
            db.commit()
            print("Seeded default books and pages.")
        else:
            print("Default books already exist.")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
