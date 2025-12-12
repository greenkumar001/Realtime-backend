# Hemut Project - Setup & Connection Guide

## Quick Overview
- **Backend**: FastAPI + SQLAlchemy (Python)
- **Frontend**: Next.js + React (TypeScript)
- **Database**: PostgreSQL (or SQLite for quick dev)
- **Real-time**: WebSocket support for live updates

---

## Prerequisites
- **Windows PowerShell** or Command Prompt
- **Python 3.9+** (`python --version`)

- **Docker Desktop** (optional, for Postgres; or install Postgres separately)

---

## Database Setup

### Option 1: Quick Start with SQLite (No Extra Install)
SQLite is already configured by default. Skip to **Backend Setup** below.

### Option 2: PostgreSQL with Docker (Recommended)

#### Install Docker Desktop
Download from https://www.docker.com/products/docker-desktop/

#### Run Postgres Container
```powershell
docker run --name hemut-postgres `
  -e POSTGRES_USER=hemut `
  -e POSTGRES_PASSWORD=secret `
  -e POSTGRES_DB=hemutdb `
  -p 5432:5432 `
  -d `
  postgres:15
```

#### Verify Postgres is Running
```powershell
docker ps
# Look for "hemut-postgres" in the list
```

#### Stop/Restart Postgres Later
```powershell
# Stop
docker stop hemut-postgres

# Start
docker start hemut-postgres

# Remove (careful!)
docker rm hemut-postgres
```

---

## Backend Setup

### 1. Create Virtual Environment
```powershell
cd "D:\Brower download files\Hemut_Project\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Create `.env` File
Copy `backend/.env.example` to `backend/.env` and edit:

```powershell
Copy-Item .env.example .env
# Edit .env with your settings (or leave defaults for SQLite)
```

**Example `.env` for Postgres:**
```
DATABASE_URL=postgresql+psycopg2://hemut:secret@localhost:5432/hemutdb
SECRET_KEY=your-super-secret-key-change-this-in-production
```

**Example `.env` for SQLite (default):**
```
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=dev-secret-key
```

### 4. Run Backend Server
```powershell
# Make sure venv is activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

Backend is now live at **http://localhost:8000**  
API docs available at **http://localhost:8000/docs**

---

## Frontend Setup

### 1. Install Node Dependencies
```powershell
cd "D:\Brower download files\Hemut_Project\hemut-frontend"
npm install
```

### 2. Create `.env.local` for API Configuration
```powershell
# In hemut-frontend directory, create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### 3. Run Development Server
```powershell
npm run dev
```

**Expected output:**
```
> next dev
Ready in X.XXs
Local:        http://localhost:3000
```

Frontend is now live at **http://localhost:3000**

---

## Verify Everything Works

### Test Backend Endpoints

#### List Questions (no auth needed)
```powershell
curl http://localhost:8000/questions
```

#### Submit a Question
```powershell
curl -X POST http://localhost:8000/questions `
  -H "Content-Type: application/json" `
  -d '{"message":"Test question from setup"}'
```

#### Register a User
```powershell
curl -X POST http://localhost:8000/register `
  -H "Content-Type: application/json" `
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'
```

#### Login
```powershell
curl -X POST http://localhost:8000/login `
  -H "Content-Type: application/json" `
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'
```

Response will include an `access_token` to use in subsequent requests.

### Test Frontend
1. Open **http://localhost:3000** in your browser
2. Navigate to `/login` or `/register`
3. Try submitting a question at the main page
4. Check browser DevTools console for any API errors

---

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/register` | POST | Register new user → returns `access_token` |
| `/login` | POST | Login user → returns `access_token` |
| `/questions` | GET | List all questions |
| `/questions` | POST | Submit new question |
| `/questions/{qid}/answer` | POST | Mark question as answered (admin only) |
| `/questions/{qid}/escalate` | POST | Escalate question |
| `/ws` | WebSocket | Real-time updates |

---

## Environment Variables Summary

**Backend (`backend/.env`):**
- `DATABASE_URL` — SQLAlchemy connection string
- `SECRET_KEY` — JWT signing key (change in production!)

**Frontend (`hemut-frontend/.env.local`):**
- `NEXT_PUBLIC_API_URL` — Backend URL (e.g., `http://localhost:8000`)

---

## Common Issues & Fixes

### Backend won't start: `ModuleNotFoundError`
```powershell
# Ensure venv is activated, then reinstall
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Postgres connection refused
```powershell
# Check if container is running
docker ps | findstr hemut-postgres

# If not, restart it
docker start hemut-postgres
```

### CORS errors in browser console
- Backend already has `allow_origins=["*"]` for development.
- If issues persist, check frontend's `NEXT_PUBLIC_API_URL` matches backend URL.

### Database locked (SQLite)
- SQLite doesn't handle concurrent writes well. Use Postgres for production.
- For local dev, just restart the backend.

---

## Production Checklist
- [ ] Change `SECRET_KEY` in `backend/.env` to a strong random string
- [ ] Use PostgreSQL (not SQLite)
- [ ] Set `allow_origins` to specific domain(s) in `main.py` CORS config
- [ ] Use HTTPS for API and frontend
- [ ] Keep `.env` file out of version control (add to `.gitignore`)
- [ ] Use a production ASGI server (e.g., Gunicorn + Uvicorn)
- [ ] Set up database backups

---

## Next Steps
1. **Run Postgres** (Docker command above)
2. **Setup backend** (venv + pip install + `.env`)
3. **Run backend** (uvicorn command)
4. **Setup frontend** (npm install + `.env.local`)
5. **Run frontend** (npm run dev)
6. **Test** in browser at http://localhost:3000

Questions? Check FastAPI docs: https://fastapi.tiangolo.com/
