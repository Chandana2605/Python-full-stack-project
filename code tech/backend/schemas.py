from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    created_at: datetime

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    tags: Optional[str]
    level: Optional[str]

class ConceptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    course_id: int
    level: Optional[str]

class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    slug: str
    definition: str
    code_snippet: Optional[str]
    example: Optional[str]
    tags: Optional[str]
    difficulty: int
    concept_id: int

class CourseDetailOut(CourseOut):
    concepts: List[ConceptOut]

class ConceptDetailOut(ConceptOut):
    topics: List[TopicOut]

class QuestionOut(BaseModel):
    topic_id: int
    mode: Literal['typing','mcq','truefalse','flashcard','speed','fillblank']
    clue_type: Literal['definition','code','example']
    clue: str
    choices: Optional[List[str]] = None
    statement: Optional[str] = None
    statement_label: Optional[str] = None
    time_limit_sec: Optional[int] = None
    blank_token: Optional[str] = None

class AnswerIn(BaseModel):
    topic_id: int
    mode: Literal['typing','mcq','truefalse','flashcard','speed','fillblank']
    clue_type: Literal['definition','code','example']
    user_answer: str
    duration_ms: Optional[int] = 0
    statement_label: Optional[str] = None
    blank_token: Optional[str] = None

class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    topic_id: int
    mode: str
    clue_type: str
    answer: str
    correct: bool
    score_awarded: int
    duration_ms: int
    created_at: datetime

class ProgressOut(BaseModel):
    total_attempts: int
    correct_attempts: int
    accuracy: float
    total_score: int
    average_time_ms: float
    by_mode: dict
    streak_days: int
    courses: List[dict]
    concepts: List[dict]
    recent: List[AttemptOut]

class LeaderboardUser(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    total_score: int
    correct_attempts: int
    total_attempts: int
