from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from backend.config import settings
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class Base(DeclarativeBase):
    """
    Base class for declarative models.
    """
    pass

DATABASE_URL = settings.DATABASE_URL or "sqlite+aiosqlite:///./ba_accelerator.db"
logger.info(f"Connecting to database at {DATABASE_URL}")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Session factory
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db_session():
    """
    Dependency helper for FastAPI endpoints.
    """
    async with AsyncSessionLocal() as session:
        yield session
