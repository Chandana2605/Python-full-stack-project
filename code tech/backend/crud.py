from sqlalchemy import select, func
from sqlalchemy.orm import Session
from models import User, Course, Concept, Topic, Attempt

def get_user_by_email(db: Session, email: str):
    return db.scalar(select(User).where(User.email == email))

def create_user(db: Session, email: str, name: str, password_hash: str) -> User:
    user = User(email=email, name=name, password_hash=password_hash)
    db.add(user); db.commit(); db.refresh(user)
    return user

def list_courses(db: Session):
    return db.scalars(select(Course).order_by(Course.title.asc())).all()

def get_course(db: Session, course_id: int):
    return db.scalar(select(Course).where(Course.id == course_id))

def list_concepts_by_course(db: Session, course_id: int):
    return db.scalars(select(Concept).where(Concept.course_id == course_id).order_by(Concept.title.asc())).all()

def get_concept(db: Session, concept_id: int):
    return db.scalar(select(Concept).where(Concept.id == concept_id))

def list_topics_by_concept(db: Session, concept_id: int):
    return db.scalars(select(Topic).where(Topic.concept_id == concept_id).order_by(Topic.title.asc())).all()

def get_topic(db: Session, topic_id: int):
    return db.scalar(select(Topic).where(Topic.id == topic_id))

def search_courses(db: Session, q: str):
    from sqlalchemy import or_
    ql = f"%{q.lower()}%"
    return db.scalars(select(Course).where(or_(func.lower(Course.title).like(ql), func.lower(Course.tags).like(ql)))).all()

def count_attempts(db: Session, user_id: int):
    return db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == user_id)) or 0

def count_correct(db: Session, user_id: int):
    return db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == user_id, Attempt.correct == True)) or 0

def sum_score(db: Session, user_id: int):
    return db.scalar(select(func.coalesce(func.sum(Attempt.score_awarded), 0)).where(Attempt.user_id == user_id)) or 0

def avg_time(db: Session, user_id: int):
    return db.scalar(select(func.coalesce(func.avg(Attempt.duration_ms), 0)).where(Attempt.user_id == user_id)) or 0.0

def attempts_by_mode(db: Session, user_id: int, mode: str):
    t = db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == user_id, Attempt.mode == mode)) or 0
    c = db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == user_id, Attempt.mode == mode, Attempt.correct == True)) or 0
    return t, c

def recent_attempts(db: Session, user_id: int, limit: int = 10):
    return db.scalars(select(Attempt).where(Attempt.user_id == user_id).order_by(Attempt.created_at.desc()).limit(limit)).all()

def create_attempt(db: Session, attempt: Attempt) -> Attempt:
    db.add(attempt); db.commit(); db.refresh(attempt)
    return attempt
