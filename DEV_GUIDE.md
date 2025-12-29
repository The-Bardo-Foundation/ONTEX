# Development Guide - AI-Augmented Clinical Trial Explorer (AI-CTE)

Complete guide for setting up, developing, and deploying the Osteosarcoma Now clinical trial system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Database Management](#database-management)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:

- **Windows 10+** (or Linux/Mac with minor adjustments)
- **Docker & Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop)
- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Git** - [Download](https://git-scm.com/)
- **PostgreSQL client tools** (optional, for manual DB inspection)

Verify installations:
```powershell
python --version
node --version
docker --version
docker-compose --version
git --version
```

---

## Quick Start

Get the entire system running locally in 5 minutes:

### 1. Clone & Navigate
```powershell
git clone <your-repo-url>
cd ONTEX
```

### 2. Start Database
```powershell
docker-compose up -d
```

This starts PostgreSQL on `localhost:5432`. Wait a few seconds for it to be ready.

### 3. Install & Run Backend (Terminal 1)
```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run backend
uvicorn app.main:app --reload --port 8000
```

Backend will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:8000/admin
- Default credentials: `admin` / `localpassword`

### 4. Install & Run Frontend (Terminal 2)
```powershell
cd frontend
npm install
npm run dev
```

Frontend will be available at: **http://localhost:5173**

### 5. You're Done! 🎉
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Admin: http://localhost:8000/admin

Stop everything with `Ctrl+C` in each terminal, or:
```powershell
docker-compose down
```

---

## Project Structure

```
ONTEX/
├── app/                          # Backend (FastAPI)
│   ├── main.py                  # Application entry point
│   ├── core/
│   │   └── config.py            # Configuration & environment
│   ├── db/
│   │   ├── database.py          # Database connection
│   │   └── models.py            # SQLAlchemy models
│   ├── api/
│   │   └── endpoints.py         # API routes
│   ├── services/
│   │   └── ingestion.py         # Data ingestion logic
│   └── admin/
│       └── views.py             # Admin panel views
│
├── frontend/                     # React + TypeScript frontend
│   ├── src/
│   │   ├── main.tsx            # Entry point
│   │   ├── App.tsx             # Root component
│   │   ├── api.ts              # API client
│   │   └── index.css           # Styles
│   └── package.json
│
├── alembic/                     # Database migrations
│   ├── versions/               # Migration files
│   ├── env.py                  # Alembic configuration
│   └── alembic.ini
│
├── docs/                        # Documentation
│   ├── MIGRATIONS.md           # Database migration guide
│   └── README.md
│
├── .env.local                  # Local development env (DO NOT COMMIT)
├── .env.railway                # Production env (DO NOT COMMIT)
├── docker-compose.yml          # Docker services
├── requirements.txt            # Python dependencies
└── Makefile                    # Convenient commands
```

---

## Development Workflow

### Daily Development Loop

```powershell
# Terminal 1: Start services
docker-compose up

# Terminal 2: Start backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Terminal 3: Start frontend
cd frontend
npm run dev
```

### Making Changes

#### Backend Changes (Python)
- Edit files in `app/`
- Uvicorn auto-reloads on file changes
- Check errors in Terminal 2
- Test at http://localhost:8000/docs

#### Frontend Changes (React/TypeScript)
- Edit files in `frontend/src/`
- Vite hot-reloads on file changes
- Check errors in Terminal 3
- Test at http://localhost:5173

#### Database Schema Changes
See [Database Management](#database-management) section below

### Code Style

**Python:**
- Follow PEP 8
- Use type hints
- Add docstrings to functions

**TypeScript/React:**
- Use ESLint: `npm run lint` in frontend/
- Use functional components
- Add prop types

---

## Database Management

### Understanding Migrations

Alembic manages database schema versions. This ensures:
- ✅ Local database matches production
- ✅ Schema changes are tracked in Git
- ✅ Easy rollback if needed

See [MIGRATIONS.md](docs/MIGRATIONS.md) for detailed guide.

### Common Database Tasks

#### Check current schema state
```powershell
alembic current              # Current revision
alembic heads               # Latest revision
alembic history             # All revisions
```

#### Make a schema change

1. **Edit your model** in `app/db/models.py`:
```python
class ClinicalTrial(Base):
    # ... existing fields ...
    new_field: Mapped[str] = mapped_column(String, nullable=True)
```

2. **Generate migration**:
```powershell
alembic revision --autogenerate -m "Add new_field to clinical_trials"
```

3. **Review the generated file** in `alembic/versions/`

4. **Test locally**:
```powershell
# Fresh database
docker-compose down -v
docker-compose up
uvicorn app.main:app --reload

# Backend will auto-run migrations on startup
```

5. **Commit**:
```powershell
git add alembic/versions/00X_*.py
git commit -m "Add migration: new_field"
```

#### Rollback (Emergency Only!)
```powershell
# Rollback last migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade 001_initial_schema
```

#### View SQL that will be executed
```powershell
alembic upgrade head --sql
```

---

## Testing

### Backend Tests

Create test files in a `tests/` directory:

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_trials():
    response = client.get("/api/trials")
    assert response.status_code == 200
```

Run tests:
```powershell
pip install pytest pytest-asyncio
pytest tests/ -v
```

### Frontend Tests

```powershell
cd frontend
npm run lint          # Check code style
npm run build        # Check if it builds
```

### Manual Testing Checklist

Before committing:

- [ ] Backend starts without errors: `uvicorn app.main:app --reload`
- [ ] Frontend compiles: `npm run dev`
- [ ] API docs load: http://localhost:8000/docs
- [ ] Admin panel loads: http://localhost:8000/admin
- [ ] Frontend loads: http://localhost:5173
- [ ] No console errors in browser DevTools
- [ ] Database migrations run: Check `alembic current`

---

## Deployment

### To Railway (Production)

1. **Ensure all tests pass locally**
```powershell
# Test backend
pytest tests/ -v

# Test frontend build
cd frontend && npm run build
```

2. **Commit & push to main**
```powershell
git add .
git commit -m "Feature: [description]"
git push origin main
```

3. **Railway auto-deploys**
   - Backend starts with environment variable `ENVIRONMENT=railway`
   - Alembic migrations run automatically
   - Frontend builds and deploys
   - Database updates with schema changes

### Environment Variables on Railway

Set these in Railway dashboard:

```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db
OPENAI_API_KEY=sk-proj-xxx
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-password
ENVIRONMENT=railway
```

### Pre-Deployment Checklist

- [ ] All tests passing locally
- [ ] Database migrations tested locally
- [ ] No hardcoded URLs/credentials
- [ ] `.env.railway` NOT committed to Git
- [ ] CORS settings updated for production domain
- [ ] OpenAI API key is valid
- [ ] Frontend API calls use correct backend URL

### Monitoring Production

After deployment:

- Check Railway dashboard for errors
- Verify API responds: `https://your-railway-app.railway.app/docs`
- Check logs for migration errors
- Test critical flows in production

---

## Troubleshooting

### Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'app'`
```powershell
# Make sure you're in project root
cd ONTEX
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

**Error:** `Cannot connect to database`
```powershell
# Check PostgreSQL is running
docker-compose ps

# Check DATABASE_URL in .env.local
# Should be: postgresql+asyncpg://postgres:localpassword@localhost:5432/osteosarcoma_db
```

**Error:** `ModuleNotFoundError: No module named 'alembic'`
```powershell
pip install -r requirements.txt
```

### Frontend Won't Start

**Error:** `Port 5173 already in use`
```powershell
# Either:
# 1. Kill process on that port, or
# 2. Run on different port:
npm run dev -- --port 5174
```

**Error:** `npm: command not found`
```powershell
# Reinstall Node.js from https://nodejs.org/
# Then verify: node --version
```

### Database Issues

**Error:** `"Relation does not exist"` after migration
```powershell
# Migrations didn't run - backend didn't start properly
# Check backend logs for migration errors

# Or manually trigger:
alembic upgrade head
```

**Error:** `"FATAL: remaining connection slots are reserved"`
```powershell
# Too many connections open
docker-compose down
docker-compose up
```

**Lost all data?**
```powershell
# If you did: docker-compose down -v
# This deletes the database volume

# Data is only lost if using -v flag!
# Without -v, data persists between restarts
```

### CORS Errors in Frontend

**Error:** `Access to XMLHttpRequest blocked by CORS`

Check [app/main.py](app/main.py) CORS configuration:
```python
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative port
    "https://your-railway-domain.app",  # Production
]
```

### Migrations Won't Run

```powershell
# Check if migrations exist
alembic history

# If no history, create initial migration:
alembic revision --autogenerate -m "Initial schema"

# Check migration file is in alembic/versions/
# Then try running backend again
```

---

## Useful Commands

### Backend
```powershell
# Run with auto-reload
uvicorn app.main:app --reload --port 8000

# Run without auto-reload
uvicorn app.main:app --port 8000 --workers 4
```

### Database
```powershell
# Start PostgreSQL
docker-compose up -d

# Stop PostgreSQL
docker-compose down

# Fresh database
docker-compose down -v && docker-compose up

# View logs
docker-compose logs postgres

# Connect with psql (if installed)
psql -h localhost -U postgres -d osteosarcoma_db
```

### Frontend
```powershell
cd frontend

# Development
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Check for errors
npm run lint
```

### Migrations
```powershell
# Create new migration
alembic revision --autogenerate -m "description"

# Upgrade to latest
alembic upgrade head

# Downgrade one
alembic downgrade -1

# View all migrations
alembic history

# View SQL (without executing)
alembic upgrade head --sql
```

---

## Getting Help

1. **Check existing issues** on GitHub
2. **Read documentation**:
   - [MIGRATIONS.md](docs/MIGRATIONS.md) - Database guide
   - [FastAPI docs](https://fastapi.tiangolo.com/)
   - [React docs](https://react.dev/)
3. **Check logs**:
   - Backend: Terminal output
   - Frontend: Browser console (F12)
   - Database: `docker-compose logs postgres`

---

## Next Steps

- [ ] Complete Quick Start above
- [ ] Make a test commit
- [ ] Try adding a field to a model (exercise migrations)
- [ ] Deploy a test change to Railway
- [ ] Set up pre-commit hooks (optional)

Happy coding! 🚀
