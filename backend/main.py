from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqladmin import Admin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.db.database import engine, Base, get_db
from app.db.models import ClinicalTrial, TrialStatus
from app.admin.views import ClinicalTrialAdmin
from app.services.ingestion import run_daily_ingestion

# Initialize Scheduler
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables (simplification for boilerplate)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Add ingestion job to run every 24 hours
    scheduler.add_job(run_daily_ingestion, 'interval', hours=24)
    scheduler.start()
    
    yield
    
    # Shutdown
    scheduler.shutdown()

app = FastAPI(title="Osteosarcoma Clinical Trial Explorer", lifespan=lifespan)

# Setup Admin
admin = Admin(app, engine)
admin.add_view(ClinicalTrialAdmin)

@app.get("/api/v1/trials")
async def get_approved_trials(db: AsyncSession = Depends(get_db)):
    """
    Get all trials with APPROVED status.
    """
    stmt = select(ClinicalTrial).where(ClinicalTrial.status == TrialStatus.APPROVED)
    result = await db.execute(stmt)
    trials = result.scalars().all()
    return trials

@app.get("/")
async def root():
    return {"message": "Clinical Trial Explorer API is running."}
