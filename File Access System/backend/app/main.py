from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, SessionLocal
from app.routes import auth_routes, admin_routes, user_routes
from app.models import User, File
from app.auth import get_password_hash

#  CREATE APP ONLY ONCE
app = FastAPI(title="Secure File Access System (SQLite)")

#  ENABLE CORS (FRONTEND CONNECTION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#  CREATE TABLES
Base.metadata.create_all(bind=engine)

# REGISTER ROUTERS
app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(user_routes.router)

# SEED ADMIN & FILES ON STARTUP
@app.on_event("startup")
def seed_data():
    db = SessionLocal()

    # Create admin if not exists
    admin = db.query(User).filter(User.role == "admin").first()
    if not admin:
        admin = User(
            email="admin@company.com",
            password=get_password_hash("admin123"),
            role="admin"
        )
        db.add(admin)
        print(" Admin created: admin@company.com / admin123")

    # Create sample files
    if db.query(File).count() == 0:
        db.add_all([
            File(name="Salary Report", description="Finance confidential file"),
            File(name="HR Records", description="Employee data"),
            File(name="Product Roadmap", description="Internal roadmap"),
        ])
        print(" Sample files created")

    db.commit()
    db.close()
