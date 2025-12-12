# backend/app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

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
