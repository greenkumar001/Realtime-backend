from fastapi import FastAPI, WebSocket, Depends, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, Question, User
from .schemas import QuestionCreate, QuestionOut, UserCreate, UserLogin, Token
from .auth import create_access_token, get_password_hash, verify_password, decode_token
from .ws_manager import manager
from typing import List, Optional
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app
app = FastAPI(
    title="Hemut Q&A Dashboard",
    description="Real-time Q&A dashboard with WebSocket support",
    version="1.0.0"
)

# CORS middleware - allow frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event - create tables
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

# Dependency injection
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: Optional[str] = None, db: Session = Depends(get_db)):
    """Extract and validate user from JWT token"""
    if not token:
        return None
    try:
        data = decode_token(token)
        if not data:
            return None
        uid = data.get("user_id")
        user = db.query(User).filter(User.user_id == uid).first()
        return user
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return None

# ==================== Authentication Endpoints ====================

@app.post("/register", response_model=Token, tags=["Auth"])
async def register(request: Request, db: Session = Depends(get_db)):
    """
    Register a new user.
    - Returns JWT access token on success
    """
    try:
        # Read raw body for debugging and parsing
        body_bytes = await request.body()
        try:
            raw = body_bytes.decode("utf-8") if body_bytes else ""
        except Exception:
            raw = str(body_bytes)
        logger.info(f"Register raw body: {raw}")

        # attempt to parse JSON body
        import json
        payload = json.loads(raw)

        # Validate payload against schema
        user_in = UserCreate(**payload)

        # Check if user already exists
        existing = db.query(User).filter(
            (User.username == user_in.username) | (User.email == user_in.email)
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )

        # Determine admin flag from optional admin_code
        is_admin_flag = False
        try:
            if getattr(user_in, "admin_code", None) and ADMIN_SECRET and user_in.admin_code == ADMIN_SECRET:
                is_admin_flag = True
        except Exception:
            is_admin_flag = False

        # Create new user
        user = User(
            username=user_in.username,
            email=user_in.email,
            password_hash=get_password_hash(user_in.password),
            is_admin=is_admin_flag
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Generate token (include is_admin)
        token = create_access_token({"user_id": user.user_id, "username": user.username, "is_admin": user.is_admin})
        logger.info(f"User registered: {user.username} (is_admin={user.is_admin})")

        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Unhandled error in /register: {e}\n{tb}")
        # Persist error details to a file for easier inspection
        try:
            with open("./register_error.log", "a", encoding="utf-8") as f:
                f.write("--- /register error ---\n")
                f.write(f"raw_body: {raw}\n")
                f.write(f"error: {e}\n")
                f.write(tb + "\n")
        except Exception:
            logger.error("Failed to write register_error.log")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@app.post("/login", response_model=Token, tags=["Auth"])
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login user with username and password.
    - Returns JWT access token on success
    """
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == credentials.username) | (User.email == credentials.username)
    ).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password"
        )
    
    # Generate token
    token = create_access_token({
        "user_id": user.user_id,
        "username": user.username,
        "is_admin": user.is_admin
    })
    logger.info(f"User logged in: {user.username}")
    
    return {"access_token": token, "token_type": "bearer"}

# ==================== Question Endpoints ====================

@app.post("/questions", response_model=QuestionOut, tags=["Questions"])
async def submit_question(q: QuestionCreate, db: Session = Depends(get_db)):
    """
    Submit a new question.
    - Validates question is not blank
    - Broadcasts to all connected WebSocket clients
    """
    if not q.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )
    
    # Create question
    question = Question(message=q.message.strip())
    db.add(question)
    db.commit()
    db.refresh(question)
    
    # Broadcast new question to all connected clients
    await manager.broadcast({
        "type": "new_question",
        "question": {
            "question_id": question.question_id,
            "user_id": question.user_id,
            "message": question.message,
            "timestamp": question.timestamp.isoformat(),
            "status": question.status,
            "escalated": question.escalated,
            "answered_by": question.answered_by
        }
    })
    
    logger.info(f"New question submitted: {question.question_id}")
    return question

@app.get("/questions", response_model=List[QuestionOut], tags=["Questions"])
def list_questions(
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="Filter by status: Pending, Escalated, Answered")
):
    """
    Get all questions, ordered by escalated status then timestamp (newest first).
    - Escalated questions appear first
    - Optional filter by status
    """
    query = db.query(Question)
    
    if status_filter:
        query = query.filter(Question.status == status_filter)
    
    questions = query.order_by(
        Question.escalated.desc(),
        desc(Question.timestamp)
    ).all()
    
    return questions

@app.get("/questions/{question_id}", response_model=QuestionOut, tags=["Questions"])
def get_question(question_id: int, db: Session = Depends(get_db)):
    """Get a single question by ID"""
    question = db.query(Question).filter(Question.question_id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    return question

@app.post("/questions/{question_id}/answer", tags=["Questions"])
async def answer_question(
    question_id: int,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Mark a question as answered (admin only).
    - Only logged-in admins can perform this action
    - Broadcasts update to all clients
    """
    question = db.query(Question).filter(Question.question_id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Check if user is admin
    user = get_current_user(token, db)
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can mark questions as answered"
        )
    
    # Update question
    question.status = "Answered"
    question.answered_by = user.user_id
    db.commit()
    db.refresh(question)
    
    # Broadcast update
    await manager.broadcast({
        "type": "question_updated",
        "question": {
            "question_id": question.question_id,
            "status": question.status,
            "answered_by": question.answered_by
        }
    })
    
    # Optional: Send webhook notification
    if WEBHOOK_URL:
        try:
            import httpx
            await httpx.AsyncClient().post(WEBHOOK_URL, json={
                "question_id": question.question_id,
                "event": "answered",
                "answered_by": user.username
            })
        except Exception as e:
            logger.error(f"Webhook failed: {e}")
    
    logger.info(f"Question {question_id} marked as answered by {user.username}")
    return {"detail": "Question marked as answered"}

@app.post("/questions/{question_id}/escalate", tags=["Questions"])
async def escalate_question(question_id: int, db: Session = Depends(get_db)):
    """
    Escalate a question (move to top, any user can do this).
    - Broadcasts update to all clients
    """
    question = db.query(Question).filter(Question.question_id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    if question.escalated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is already escalated"
        )
    
    # Update question
    question.escalated = True
    question.status = "Escalated"
    db.commit()
    db.refresh(question)
    
    # Broadcast update
    await manager.broadcast({
        "type": "question_updated",
        "question": {
            "question_id": question.question_id,
            "status": question.status,
            "escalated": question.escalated
        }
    })
    
    logger.info(f"Question {question_id} escalated")
    return {"detail": "Question escalated"}

# ==================== WebSocket Endpoint ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    - Sends new questions to all connected clients
    - Sends question updates (status changes) to all clients
    """
    await manager.connect(websocket)
    logger.info("Client connected to WebSocket")
    
    try:
        while True:
            # Keep connection alive, receive heartbeats
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except Exception as e:
        logger.info(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# ==================== Health Check ====================

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Hemut Q&A Dashboard"}


@app.post("/suggest", tags=["RAG"])
def suggest_answer(payload: dict):
    """
    Mock RAG-style suggestion endpoint.
    Expects JSON { "question": "..." }
    Returns a list of suggested answers (mocked).
    """
    try:
        q = payload.get("question") if isinstance(payload, dict) else None
        if not q or not str(q).strip():
            raise HTTPException(status_code=400, detail="question is required")

        # Mocked suggestions - in a real RAG system this would call a retriever + generator
        suggestions = [
            {
                "id": "s1",
                "text": f"Short answer: You can reset your password by visiting Settings > Password and following the prompts. If you use OAuth, follow provider-specific steps. (Context-aware suggestion for: {q[:80]})",
                "confidence": 0.86,
                "source": "mock_kb:reset_password"
            },
            {
                "id": "s2",
                "text": f"Step-by-step: 1) Go to your profile. 2) Click 'Change password'. 3) Enter current and new password. 4) Confirm via email if required. (Suggested for: {q[:80]})",
                "confidence": 0.78,
                "source": "mock_kb:howto_reset"
            }
        ]

        return {"question": q, "suggestions": suggestions}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/suggest error: {e}")
        raise HTTPException(status_code=500, detail="Suggestion generation failed")

# ==================== API Documentation ====================

@app.get("/", tags=["Info"])
def root():
    """API information"""
    return {
        "name": "Hemut Q&A Dashboard API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": ["/register", "/login"],
            "questions": ["/questions", "/questions/{id}", "/questions/{id}/answer", "/questions/{id}/escalate"],
            "websocket": ["/ws"],
            "health": ["/health"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
