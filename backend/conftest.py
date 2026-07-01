import asyncio
import pytest
from backend.db.postgres import engine, Base
# Import all database models to register with Base
from backend.db.models import Job, Requirement, Story, AuditLog
from backend.validation_export.db_models import (
    ValidationResultDB, ValidationFindingDB, BAReviewDB,
    AuditEventDB, RevisionPackageDB, ValidatedStoryPackageDB
)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Automatically creates all tables in the test database before running tests.
    """
    # SQLite does not support drop_all cleanly if connection is open, but create_all is safe
    async def _init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    try:
        # Try to run in current event loop if exists, or create a new one
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_init_db())
        else:
            loop.run_until_complete(_init_db())
    except Exception:
        asyncio.run(_init_db())
        
    yield
