from app.database import db

def create_user(user: dict):
    db.users.insert_one(user)

def get_user(username: str):
    return db.users.find_one({"username": username})
