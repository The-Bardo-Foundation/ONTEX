from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# --- THE FIX IS HERE ---
# Railway provides "postgresql://", but asyncpg needs "postgresql+asyncpg://"
db_url = settings.DATABASE_URL
if db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Now use the modified 'db_url' instead of 'settings.DATABASE_URL'
engine = create_async_engine(db_url, echo=False)
# -----------------------

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        yield session