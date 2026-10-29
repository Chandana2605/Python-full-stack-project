
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from typing import Optional, Literal, List, Dict
import random, re, difflib

from database import engine, Base, SessionLocal
from models import User, Course, Concept, Topic, Attempt
from schemas import (
    UserCreate, UserOut, TokenOut,
    CourseOut, CourseDetailOut, ConceptOut, ConceptDetailOut, TopicOut,
    QuestionOut, AnswerIn, AttemptOut, ProgressOut, LeaderboardUser
)
from crud import (
    get_user_by_email, create_user,
    list_courses, get_course, list_concepts_by_course, get_concept, list_topics_by_concept, get_topic, search_courses,
    count_attempts, count_correct, sum_score, avg_time, attempts_by_mode, recent_attempts, create_attempt
)
from auth import get_db, get_password_hash, verify_password, create_access_token, get_current_user

# Create DB schema if not exists
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tech Duolingo v3 API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# ---------- SEED DEFAULTS ----------
def seed_defaults(db: Session) -> Dict:
    """
    Create default Courses → Concepts → Topics if DB is empty.
    Each Topic: definition, code_snippet, example, tags, difficulty.
    Course/Concept carry level: basic | intermediate | advanced.
    """
    if db.scalar(select(func.count(Course.id))) or 0:
        return {"status": "skipped", "reason": "courses already exist"}

    catalog: List[Dict] = [
        {
            "title": "Backend Basics",
            "description": "HTTP, REST, APIs, authentication",
            "tags": "backend,api,auth",
            "level": "basic",
            "concepts": [
                {
                    "title": "HTTP & REST",
                    "description": "Core HTTP/REST concepts",
                    "level": "basic",
                    "topics": [
                        {
                            "slug": "http-api",
                            "title": "API",
                            "definition": "Programmatic interface over HTTP for communicating with services.",
                            "code_snippet": "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/hello')\ndef hello(): return {'msg': 'world'}",
                            "example": "Mobile app calling a REST endpoint to fetch a profile.",
                            "tags": "http,rest,backend",
                            "difficulty": 1,
                        },
                        {
                            "slug": "rest-principles",
                            "title": "REST Principles",
                            "definition": "Statelessness, resource URIs, representations, standard methods.",
                            "code_snippet": "# GET /users/123 -> returns JSON representation of user 123",
                            "example": "Use GET for reads, POST for creation, PUT/PATCH for updates, DELETE to remove.",
                            "tags": "rest,design",
                            "difficulty": 2,
                        },
                    ],
                },
                {
                    "title": "Authentication",
                    "description": "JWT and OAuth2 overview",
                    "level": "intermediate",
                    "topics": [
                        {
                            "slug": "jwt-basic",
                            "title": "JWT",
                            "definition": "Signed token that carries claims; used to authenticate API requests.",
                            "code_snippet": "from jose import jwt\njwt.encode({'sub':'alice'}, 'secret', algorithm='HS256')",
                            "example": "Client sends Authorization: Bearer <token>.",
                            "tags": "auth,jwt,security",
                            "difficulty": 2,
                        },
                        {
                            "slug": "oauth2-overview",
                            "title": "OAuth2",
                            "definition": "Authorization framework to delegate access (Auth Code flow).",
                            "code_snippet": "# /authorize -> user -> /token -> access_token",
                            "example": "Login with Google delegates identity to provider.",
                            "tags": "auth,oauth2",
                            "difficulty": 3,
                        },
                    ],
                },
            ],
        },
        {
            "title": "Frontend Foundations",
            "description": "React components, state, and styling",
            "tags": "react,ui,css",
            "level": "basic",
            "concepts": [
                {
                    "title": "React Basics",
                    "description": "Components and state",
                    "level": "basic",
                    "topics": [
                        {
                            "slug": "react-state",
                            "title": "React State",
                            "definition": "Local component data managed with useState.",
                            "code_snippet": "const [count, setCount] = useState(0);\n<button onClick={()=>setCount(count+1)}>+</button>",
                            "example": "Counter increments on click.",
                            "tags": "react,state",
                            "difficulty": 1,
                        },
                        {
                            "slug": "react-hooks",
                            "title": "React Hooks",
                            "definition": "Lifecycle and side-effects via useEffect.",
                            "code_snippet": "useEffect(()=>{ document.title = `Count ${count}` }, [count]);",
                            "example": "Update page title when count changes.",
                            "tags": "react,hooks",
                            "difficulty": 2,
                        },
                    ],
                },
                {
                    "title": "Styling",
                    "description": "Modern CSS techniques",
                    "level": "intermediate",
                    "topics": [
                        {
                            "slug": "css-flexbox",
                            "title": "CSS Flexbox",
                            "definition": "Flex container aligns items along a row/column.",
                            "code_snippet": ".row{display:flex;gap:8px;align-items:center}",
                            "example": "Align buttons in a row with spacing.",
                            "tags": "css,layout",
                            "difficulty": 1,
                        },
                        {
                            "slug": "css-grid",
                            "title": "CSS Grid",
                            "definition": "Two-dimensional layout with rows and columns.",
                            "code_snippet": ".grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}",
                            "example": "Responsive card grid.",
                            "tags": "css,grid",
                            "difficulty": 2,
                        },
                    ],
                },
            ],
        },
        {
            "title": "Auth & Security",
            "description": "Tokens, sessions, and OAuth2",
            "tags": "jwt,oauth2,security",
            "level": "intermediate",
            "concepts": [
                {
                    "title": "Tokens",
                    "description": "JWT details",
                    "level": "basic",
                    "topics": [
                        {
                            "slug": "jwt-token",
                            "title": "JWT Token",
                            "definition": "Base64-encoded header.payload.signature used for stateless auth.",
                            "code_snippet": "jwt.encode({'sub':'alice'}, 'secret', algorithm='HS256')",
                            "example": "Client keeps JWT and sends as Bearer token.",
                            "tags": "jwt,token",
                            "difficulty": 2,
                        },
                    ],
                },
                {
                    "title": "Sessions",
                    "description": "Server-side authentication",
                    "level": "intermediate",
                    "topics": [
                        {
                            "slug": "session-cookies",
                            "title": "Session Cookies",
                            "definition": "Server stores session; client keeps cookie with session id.",
                            "code_snippet": "# Set-Cookie: session_id=abc123; HttpOnly; Secure; SameSite=Strict",
                            "example": "Web app with server-managed session.",
                            "tags": "session,cookies",
                            "difficulty": 2,
                        },
                    ],
                },
                {
                    "title": "OAuth2",
                    "description": "Auth Code flow",
                    "level": "advanced",
                    "topics": [
                        {
                            "slug": "oauth2-auth-code-flow",
                            "title": "Auth Code Flow",
                            "definition": "Client gets code at /authorize, exchanges at /token for access_token.",
                            "code_snippet": "# /authorize -> code -> /token -> access_token + refresh_token",
                            "example": "External provider login (Google).",
                            "tags": "oauth2,flow",
                            "difficulty": 3,
                        },
                    ],
                },
            ],
        },
        {
            "title": "DevOps Essentials",
            "description": "Containers, orchestration, and CI/CD",
            "tags": "docker,k8s,ci/cd",
            "level": "basic",
            "concepts": [
                {
                    "title": "Containers",
                    "description": "Docker basics",
                    "level": "basic",
                    "topics": [
                        {
                            "slug": "docker-basics",
                            "title": "Docker Basics",
                            "definition": "Package apps as images and run containers consistently.",
                            "code_snippet": "docker build -t app .\ndocker run -p 8080:8080 app",
                            "example": "Run the same app locally and in prod.",
                            "tags": "docker,containers",
                            "difficulty": 2,
                        },
                    ],
                },
                {
                    "title": "Orchestration",
                    "description": "Kubernetes fundamentals",
                    "level": "intermediate",
                    "topics": [
                        {
                            "slug": "k8s-deployment",
                            "title": "K8s Deployment",
                            "definition": "Declarative object for managing replica Pods.",
                            "code_snippet": "apiVersion: apps/v1\nkind: Deployment\nspec:\n  replicas: 3\n  template:\n    spec:\n      containers:\n        - name: app\n          image: myapp:latest",
                            "example": "Scale app across nodes.",
                            "tags": "k8s,deployment",
                            "difficulty": 3,
                        },
                    ],
                },
                {
                    "title": "CI/CD",
                    "description": "Build/test/deploy pipelines",
                    "level": "advanced",
                    "topics": [
                        {
                            "slug": "ci-cd-pipeline",
                            "title": "CI/CD Pipeline",
                            "definition": "Automate build, test, and deploy on commits.",
                            "code_snippet": "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v3\n      - run: npm ci && npm test",
                            "example": "Run tests per push, deploy on tag.",
                            "tags": "ci,cd,automation",
                            "difficulty": 2,
                        },
                    ],
                },
            ],
        },
        {
            "title": "Databases & ORMs",
            "description": "SQL, schemas, and ORM mapping",
            "tags": "sql,postgres,orm",
            "level": "intermediate",
            "concepts": [
                {
                    "title": "Relational DBs",
                    "description": "SQL basics",
                    "level": "basic",
                    "topics": [
                        {
                            "slug": "sql-basics",
                            "title": "SQL Basics",
                            "definition": "Create tables, query data, filter with WHERE, join related data.",
                            "code_snippet": "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);\nSELECT * FROM users WHERE id=1;",
                            "example": "Store and query user records.",
                            "tags": "sql,db",
                            "difficulty": 1,
                        },
                    ],
                },
                {
                    "title": "ORM",
                    "description": "Mapping objects to tables",
                    "level": "intermediate",
                    "topics": [
                        {
                            "slug": "sqlalchemy-orm",
                            "title": "SQLAlchemy ORM",
                            "definition": "Use declarative models and sessions to persist Python objects.",
                            "code_snippet": "user = User(name='Alice')\ndb.add(user); db.commit(); db.refresh(user)",
                            "example": "Create & read users with ORM.",
                            "tags": "orm,sqlalchemy",
                            "difficulty": 2,
                        },
                    ],
                },
                {
                    "title": "Indexing & Performance",
                    "description": "Basic indexing strategies",
                    "level": "advanced",
                    "topics": [
                        {
                            "slug": "indexing-basics",
                            "title": "Indexing Basics",
                            "definition": "Create indexes to speed up lookups and sorts on columns.",
                            "code_snippet": "CREATE INDEX idx_users_name ON users(name);",
                            "example": "Fast search by user name using index.",
                            "tags": "db,index",
                            "difficulty": 2,
                        },
                    ],
                },
            ],
        },
    ]

    created = {"courses": 0, "concepts": 0, "topics": 0}
    for course_data in catalog:
        course = Course(
            title=course_data["title"],
            description=course_data["description"],
            tags=course_data["tags"],
            level=course_data.get("level"),
        )
        db.add(course); db.flush()

        for concept_data in course_data["concepts"]:
            concept = Concept(
                title=concept_data["title"],
                description=concept_data["description"],
                level=concept_data.get("level"),
                course_id=course.id,
            )
            db.add(concept); db.flush()

            for t in concept_data["topics"]:
                if db.scalar(select(Topic).where(Topic.slug == t["slug"])):
                    continue
                topic = Topic(
                    title=t["title"],
                    slug=t["slug"],
                    definition=t["definition"],
                    code_snippet=t["code_snippet"],
                    example=t["example"],
                    tags=t["tags"],
                    difficulty=t["difficulty"],
                    concept_id=concept.id,
                )
                db.add(topic); created["topics"] += 1

            created["concepts"] += 1
        created["courses"] += 1

    db.commit()
    return {"status": "ok", "created": created}

# Seed on startup (only when empty)
@app.on_event("startup")
def startup_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _ = seed_defaults(db)
    finally:
        db.close()

# ---------- Helpers for game ----------
SYNONYMS = {
    "api": ["rest api", "web api", "http api"],
    "jwt": ["json web token"],
    "docker": ["container", "containers"],
    "database": ["db", "sql"],
    "oauth2": ["oauth", "auth2"],
}
def sanitize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())

def evaluate_typing(answer: str, expected: str) -> tuple[bool, int]:
    a, e = sanitize(answer), sanitize(expected)
    if not a: return False, 0
    if a == e: return True, 10
    if a in [sanitize(x) for x in SYNONYMS.get(expected.lower(), [])]: return True, 8
    if e in a or a in e: return True, 6
    if difflib.SequenceMatcher(None, a, e).ratio() >= 0.75: return True, 4
    return False, 0

def score_with_time(base: int, duration_ms: int, limit_ms: int) -> int:
    if duration_ms <= 0 or limit_ms <= 0: return base
    speed_factor = max(0.0, min(1.0, (limit_ms - duration_ms) / limit_ms))
    return base + int(5 * speed_factor)

@app.get("/")
def root():
    return {"message": "Tech Duolingo v3 API running"}

# ---------- Auth ----------
@app.post("/auth/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        email = payload.email.strip().lower()
        name = payload.name.strip()
        if len(payload.password) < 6:
            raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
        existing = get_user_by_email(db, email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user = create_user(db, email=email, name=name, password_hash=get_password_hash(payload.password))
        return user
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Signup failed due to a server error")

@app.post("/auth/login", response_model=TokenOut)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_email(db, form_data.username.strip().lower())
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

# ---------- Catalog ----------
@app.get("/courses", response_model=list[CourseOut])
def api_list_courses(db: Session = Depends(get_db)):
    return list_courses(db)

@app.get("/courses/{course_id}", response_model=CourseDetailOut)
def api_get_course(course_id: int, db: Session = Depends(get_db)):
    course = get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    concepts = list_concepts_by_course(db, course_id)
    return {"id": course.id, "title": course.title, "description": course.description, "tags": course.tags, "level": course.level, "concepts": concepts}

@app.get("/concepts/{concept_id}", response_model=ConceptDetailOut)
def api_get_concept(concept_id: int, db: Session = Depends(get_db)):
    concept = get_concept(db, concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    topics = list_topics_by_concept(db, concept_id)
    return {"id": concept.id, "title": concept.title, "description": concept.description, "course_id": concept.course_id, "level": concept.level, "topics": topics}

@app.get("/topics/{topic_id}", response_model=TopicOut)
def api_get_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = get_topic(db, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic

@app.get("/search/courses", response_model=list[CourseOut])
def api_search_courses(q: str = "", db: Session = Depends(get_db)):
    return search_courses(db, q)

# ---------- Game ----------
MODES = ['typing','mcq','truefalse','flashcard','speed','fillblank']

@app.get("/game/next", response_model=QuestionOut)
def next_question(
    mode: Literal['typing','mcq','truefalse','flashcard','speed','fillblank'] = 'typing',
    course_id: Optional[int] = None, concept_id: Optional[int] = None, topic_id: Optional[int] = None,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if topic_id:
        t = get_topic(db, topic_id); topics = [t] if t else []
    elif concept_id:
        topics = list_topics_by_concept(db, concept_id)
    elif course_id:
        concepts = list_concepts_by_course(db, course_id); topics = []
        for con in concepts:
            topics.extend(list_topics_by_concept(db, con.id))
    else:
        topics = db.scalars(select(Topic)).all()

    topics = [t for t in topics if t]
    if not topics:
        raise HTTPException(status_code=404, detail="No topics available. DB might be empty.")

    # less-practiced first
    counts = {t.id: (db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == current_user.id, Attempt.topic_id == t.id)) or 0) for t in topics}
    min_count = min(counts.values()) if counts else 0
    candidates = [t for t in topics if counts[t.id] == min_count]
    topic = random.choice(candidates)

    clue_type = 'definition'; clue = topic.definition
    if mode in ['typing','mcq','truefalse','speed','fillblank']:
        choices = ['code_snippet','example','definition']; random.shuffle(choices)
        for ct in choices:
            val = getattr(topic, ct if ct != 'definition' else 'definition')
            if val:
                clue_type = 'code' if ct == 'code_snippet' else ('example' if ct == 'example' else 'definition')
                clue = val; break
    elif mode == 'flashcard':
        clue_type = 'definition'; clue = topic.definition

    time_limit_sec = 20 if mode == 'speed' else (30 if mode == 'typing' else (25 if mode == 'fillblank' else None))
    q = {"topic_id": topic.id, "mode": mode, "clue_type": clue_type, "clue": clue, "time_limit_sec": time_limit_sec}

    if mode == 'mcq':
        distractors = [t.title for t in topics if t.id != topic.id]; random.shuffle(distractors)
        choices = [topic.title] + distractors[:3]; random.shuffle(choices)
        q["choices"] = choices
    elif mode == 'truefalse':
        is_true = random.random() < 0.5
        label = topic.title if is_true else random.choice([t.title for t in topics if t.id != topic.id])
        q["statement"] = f"This clue describes: {label}"
        q["statement_label"] = label
    elif mode == 'fillblank' and clue_type == 'code':
        tokens = re.findall(r"[A-Za-z_]{3,}", clue)
        token = tokens and random.choice(tokens) or None
        if token:
            q["blank_token"] = token
            q["clue"] = clue.replace(token, "___", 1)
    return q

@app.post("/game/submit", response_model=AttemptOut)
def submit_answer(payload: AnswerIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    topic = get_topic(db, payload.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    correct, base_score = False, 0
    limit_ms = 20000 if payload.mode == 'speed' else (30000 if payload.mode == 'typing' else (25000 if payload.mode == 'fillblank' else 0))
    if payload.mode in ['typing','speed']:
        correct, base_score = evaluate_typing(payload.user_answer, topic.title)
        score = score_with_time(base_score, payload.duration_ms or 0, limit_ms)
    elif payload.mode == 'mcq':
        correct = sanitize(payload.user_answer) == sanitize(topic.title); score = 8 if correct else 0
    elif payload.mode == 'truefalse':
        user_true = payload.user_answer.lower() in ['true','t','yes','y']
        label = (payload.statement_label or '').strip(); actual = sanitize(label) == sanitize(topic.title)
        correct = (actual == user_true); score = 6 if correct else 0
    elif payload.mode == 'flashcard':
        correct = True; score = 2
    elif payload.mode == 'fillblank':
        expected = sanitize(payload.blank_token or ''); got = sanitize(payload.user_answer)
        correct = (expected and got == expected); score = 7 if correct else 0
    else:
        raise HTTPException(status_code=400, detail="Invalid mode")

    attempt = Attempt(
        user_id=current_user.id, topic_id=topic.id, mode=payload.mode, clue_type=payload.clue_type,
        answer=payload.user_answer, correct=bool(correct), score_awarded=score, duration_ms=payload.duration_ms or 0
    )
    attempt = create_attempt(db, attempt)
    return attempt

# ---------- Progress ----------
@app.get("/progress/me", response_model=ProgressOut)
def my_progress(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_attempts = count_attempts(db, current_user.id)
    correct_attempts = count_correct(db, current_user.id)
    total_score = sum_score(db, current_user.id)
    avg_time_val = avg_time(db, current_user.id)
    accuracy = float(correct_attempts)/total_attempts if total_attempts else 0.0

    dates = db.scalars(select(func.date(Attempt.created_at)).where(Attempt.user_id == current_user.id).group_by(func.date(Attempt.created_at))).all()
    streak = 0
    if dates:
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        dset = {datetime.fromisoformat(str(d)).date() for d in dates}
        while (today - timedelta(days=streak)) in dset:
            streak += 1

    modes = ['typing','mcq','truefalse','flashcard','speed','fillblank']
    by_mode = {}
    for m in modes:
        t, c = attempts_by_mode(db, current_user.id, m)
        by_mode[m] = {"attempts": t, "correct": c, "accuracy": (float(c)/t if t else 0.0)}

    courses = []
    for course in list_courses(db):
        concept_ids = [ct.id for ct in list_concepts_by_course(db, course.id)]
        topic_ids = [t.id for cid in concept_ids for t in list_topics_by_concept(db, cid)]
        attempted = db.scalar(select(func.count(func.distinct(Attempt.topic_id))).where(Attempt.user_id == current_user.id, Attempt.topic_id.in_(topic_ids))) or 0
        corrects = db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == current_user.id, Attempt.topic_id.in_(topic_ids), Attempt.correct == True)) or 0
        courses.append({"course_id": course.id, "title": course.title, "attempted_topics": attempted, "total_topics": len(topic_ids), "correct_attempts": corrects, "level": course.level})

    concepts = []
    for concept in db.scalars(select(Concept)).all():
        topic_ids = [t.id for t in list_topics_by_concept(db, concept.id)]
        if topic_ids:
            attempted = db.scalar(select(func.count(func.distinct(Attempt.topic_id))).where(Attempt.user_id == current_user.id, Attempt.topic_id.in_(topic_ids))) or 0
            corrects = db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == current_user.id, Attempt.topic_id.in_(topic_ids), Attempt.correct == True)) or 0
            concepts.append({"concept_id": concept.id, "title": concept.title, "attempted_topics": attempted, "total_topics": len(topic_ids), "correct_attempts": corrects, "level": concept.level})

    recent = recent_attempts(db, current_user.id)

    return {
        "total_attempts": total_attempts,
        "correct_attempts": correct_attempts,
        "accuracy": accuracy,
        "total_score": total_score,
        "average_time_ms": float(avg_time_val),
        "by_mode": by_mode,
        "streak_days": streak,
        "courses": courses,
        "concepts": concepts,
        "recent": recent
    }

# ---------- Leaderboard ----------
@app.get("/leaderboard", response_model=list[LeaderboardUser])
def leaderboard(db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            User.id.label('user_id'), User.name, User.email,
            func.coalesce(func.sum(Attempt.score_awarded), 0).label('total_score'),
            func.count(Attempt.id).label('total_attempts'),
            func.sum(case((Attempt.correct == True, 1), else_=0)).label('correct_attempts')
        ).outerjoin(Attempt, Attempt.user_id == User.id)
         .group_by(User.id)
         .order_by(func.coalesce(func.sum(Attempt.score_awarded), 0).desc())
         .limit(10)
    ).all()
    return [{
        "user_id": r.user_id, "name": r.name, "email": r.email,
        "total_score": r.total_score or 0, "correct_attempts": r.correct_attempts or 0,
        "total_attempts": r.total_attempts or 0
    } for r in rows]
