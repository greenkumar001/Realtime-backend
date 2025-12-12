# backend/app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from typing import List

class QuestionCreate(BaseModel):
    message: str = Field(..., min_length=1)

class QuestionOut(BaseModel):
    question_id: int
    user_id: Optional[int]
    message: str
    timestamp: datetime
    status: str
    escalated: bool
    answered_by: Optional[int]
    answers: List["AnswerOut"] = []

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    admin_code: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AnswerCreate(BaseModel):
    content: str = Field(..., min_length=1)


class AnswerOut(BaseModel):
    answer_id: int
    question_id: int
    author_id: Optional[int]
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True


# Pydantic forward refs
QuestionOut.update_forward_refs()
