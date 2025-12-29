from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqladmin import Admin
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from alembic.config import Config
from pathlib import Path
from alembic import command
import os
import asyncio

from app.core.config import settings
from app.db.database import engine, Base, get_db
from app.db.models import ClinicalTrial, TrialStatus
from app.admin.views import ClinicalTrialAdmin
from app.api.endpoints import router as api_router

# Initialize Scheduler
scheduler = AsyncIOScheduler()

async def run_migrations():
    """Run Alembic migrations or create tables for local sqlite on startup.

    - If `SKIP_MIGRATIONS=1` is set, do nothing.
    - If using `sqlite+aiosqlite`, create tables from `Base.metadata` using
      the async engine so we don't hit greenlet/async driver issues.
    - Otherwise, run Alembic's `upgrade head` in a thread to avoid blocking
      the async event loop.
    """
    # Ensure we point to the repository's alembic.ini
    repo_root = Path(__file__).resolve().parents[1]
    alembic_ini = repo_root / "alembic" / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))

    db_url = settings.DATABASE_URL or ""

    if os.getenv("SKIP_MIGRATIONS", "0") == "1":
        print("run_migrations: SKIP_MIGRATIONS=1 set, skipping automatic alembic upgrade")
        return

    # If using async sqlite, create metadata tables via async engine
    if db_url.startswith("sqlite+aiosqlite"):
        print("run_migrations: detected sqlite+aiosqlite — creating tables if missing")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("run_migrations: sqlite tables ensured via metadata.create_all")
        except Exception as e:
            print("run_migrations: error creating sqlite tables:", e)
            raise
        return

    # For other DBs, coerce asyncpg marker to sync form for Alembic and run in thread
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "", 1)

    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # Run Alembic in a thread to avoid blocking the event loop
    def _run_alembic():
        command.upgrade(alembic_cfg, "head")

    print("run_migrations: running alembic.upgrade in thread")
    try:
        await asyncio.to_thread(_run_alembic)
        print("run_migrations: alembic upgrade completed")
    except Exception:
        print("run_migrations: alembic upgrade failed")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Trace: help diagnose startup hangs
    print("startup: entering lifespan - running migrations")
    try:
        await run_migrations()
        print("startup: run_migrations() completed")
    except Exception as e:
        import traceback
        print("startup: run_migrations() raised:", e)
        traceback.print_exc()
        raise

    print("startup: scheduling ingestion job")
    try:
        scheduler.add_job(run_daily_ingestion, 'interval', hours=24)
        print("startup: added ingestion job")
        scheduler.start()
        print("startup: scheduler.start() returned")
    except Exception as e:
        import traceback
        print("startup: scheduler failed to start:", e)
        traceback.print_exc()
        raise

    print("startup: lifespan yield - application should be starting now")
    yield

    print("shutdown: lifespan - shutting down scheduler")
    try:
        scheduler.shutdown()
        print("shutdown: scheduler.shutdown() completed")
    except Exception as e:
        print("shutdown: scheduler.shutdown() raised:", e)

app = FastAPI(title="Osteosarcoma Clinical Trial Explorer", lifespan=lifespan)

# CORS configuration
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",
    "https://my-railway-url.app", # Replace with actual domain if known
    "*" # Allow all for simplicity in this context, refine for production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Admin
admin = Admin(app, engine)
admin.add_view(ClinicalTrialAdmin)

# Include API Router
app.include_router(api_router, prefix="/api/v1")

@app.post("/api/v1/debug/run-ingestion")
async def debug_ingestion():
    # Import dynamically so tests can monkeypatch `app.services.ingestion.run_daily_ingestion`
    import app.services.ingestion as ingestion
    await ingestion.run_daily_ingestion()
    return {"status": "started"}

# Mount static files
# Only mount if the directory exists (it will in Docker, maybe not in local dev unless built)
static_dir = os.path.join(os.path.dirname(__file__), "static") # Assumes /app/static in docker
if not os.path.exists(static_dir):
    # Fallback for local development or if static dir is different
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Check if API request first (though API router handles matches before this if included first? No, path matches are tricky)
    # Actually, if we use app.mount for static, specific paths are handled.
    # The Catch-all should be last.
    
    if full_path.startswith("api"):
        return {"error": "API route not found"}
        
    # Serve index.html for SPA
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Frontend not built or found at " + static_dir}
