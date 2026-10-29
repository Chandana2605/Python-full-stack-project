from app.database import db
from app.core.roles import ADMIN, USER
from app.core.security import hash_password

def seed_data():
    # 1️⃣ Seed Admin
    admin = db.users.find_one({"role": ADMIN})
    if not admin:
        db.users.insert_one({
            "username": "admin",
            "password": hash_password("admin123"),
            "role": ADMIN
        })

    # 2️⃣ Seed Employee
    employee = db.users.find_one({"username": "employee"})
    if not employee:
        db.users.insert_one({
            "username": "employee",
            "password": hash_password("employee123"),
            "role": USER
        })

    # 3️⃣ Seed Files (metadata only)
    if db.files.count_documents({}) == 0:
        db.files.insert_many([
            {
                "filename": "Salary_Report.pdf",
                "description": "Monthly salary details"
            },
            {
                "filename": "HR_Policy.pdf",
                "description": "Company HR policies"
            },
            {
                "filename": "Project_Plan.docx",
                "description": "Internal project planning document"
            }
        ])
