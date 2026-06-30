from sqlalchemy.orm import DeclarativeBase
from backend.config import settings
from backend.shared.logger import get_logger
import re

logger = get_logger(__name__)

class Base(DeclarativeBase):
    """
    Base class for declarative models.
    """
    pass

# Simple in-memory database store
class InMemoryDB:
    def __init__(self):
        self.jobs = {}
        self.requirements = []
        self.stories = []
        self.validation_results = []
        self.validation_findings = []
        self.revision_packages = []
        self.audit_events = []
        self.audit_logs = []

db_store = InMemoryDB()

class MockScalarResult:
    def __init__(self, data):
        self.data = data
    def all(self):
        return self.data
    def first(self):
        return self.data[0] if self.data else None

class MockResult:
    def __init__(self, data):
        self._data = data
    def scalar_one_or_none(self):
        return self._data[0] if self._data else None
    def scalar(self):
        return self._data[0] if self._data else None
    def scalars(self):
        return MockScalarResult(self._data)

class MockSession:
    def __init__(self):
        pass

    def add(self, instance):
        name = instance.__class__.__name__
        if name == "Job":
            db_store.jobs[instance.id] = instance
        elif name == "Requirement":
            db_store.requirements.append(instance)
        elif name == "Story":
            db_store.stories.append(instance)
        elif name == "ValidationResultDB":
            db_store.validation_results.append(instance)
        elif name == "ValidationFindingDB":
            db_store.validation_findings.append(instance)
        elif name == "RevisionPackageDB":
            db_store.revision_packages.append(instance)
        elif name == "AuditEventDB":
            db_store.audit_events.append(instance)
        elif name == "AuditLog":
            db_store.audit_logs.append(instance)

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass

    async def execute(self, stmt, *args, **kwargs):
        stmt_str = str(stmt)
        
        # 1. Handle select/find jobs
        if "from jobs" in stmt_str or "FROM jobs" in stmt_str:
            job_id = None
            if hasattr(stmt, "compile"):
                try:
                    params = stmt.compile().params
                    job_id = params.get("id_1") or params.get("job_id_1") or params.get("id")
                except Exception:
                    pass
            if not job_id:
                # parse via regex
                m = re.search(r"jobs\.id\s*=\s*:([a-zA-Z0-9_]+)", stmt_str)
                if m:
                    job_id = m.group(1)
            
            if job_id and job_id in db_store.jobs:
                return MockResult([db_store.jobs[job_id]])
            # Return list of all jobs
            return MockResult(list(db_store.jobs.values()))

        # 2. Handle select stories
        elif "from stories" in stmt_str or "FROM stories" in stmt_str:
            job_id = None
            if hasattr(stmt, "compile"):
                try:
                    params = stmt.compile().params
                    job_id = params.get("job_id_1") or params.get("job_id")
                except Exception:
                    pass
            if job_id:
                matched = [s for s in db_store.stories if s.job_id == job_id]
                return MockResult(matched)
            return MockResult(db_store.stories)

        # 3. Handle delete requirements
        elif "DELETE FROM requirements" in stmt_str or "delete from requirements" in stmt_str:
            job_id = None
            if hasattr(stmt, "compile"):
                try:
                    params = stmt.compile().params
                    job_id = params.get("job_id_1") or params.get("job_id")
                except Exception:
                    pass
            if job_id:
                db_store.requirements = [r for r in db_store.requirements if r.job_id != job_id]

        # 4. Handle delete stories
        elif "DELETE FROM stories" in stmt_str or "delete from stories" in stmt_str:
            job_id = None
            if hasattr(stmt, "compile"):
                try:
                    params = stmt.compile().params
                    job_id = params.get("job_id_1") or params.get("job_id")
                except Exception:
                    pass
            if job_id:
                db_store.stories = [s for s in db_store.stories if s.job_id != job_id]

        return MockResult([])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

# Mock Session Factory
def AsyncSessionLocal():
    return MockSession()

# Dependency Helper
async def get_db_session():
    async with MockSession() as session:
        yield session

# Mock Engine
class MockEngine:
    def begin(self):
        class MockConn:
            async def run_sync(self, func, *args, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return MockConn()


engine = MockEngine()
