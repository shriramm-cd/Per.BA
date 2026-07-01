import os
import sys

# Add the framework directory to sys.path to allow importing designlab_core directly
framework_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../framework"))
if framework_path not in sys.path:
    sys.path.insert(0, framework_path)

import uvicorn
from fastapi import FastAPI, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from backend.config import settings
from backend.db.postgres import get_db_session, engine, Base
# Import all database models to register with Base
from backend.db.models import Job, Requirement, Story, AuditLog
from backend.validation_export.db_models import (
    ValidationResultDB, ValidationFindingDB, BAReviewDB,
    AuditEventDB, RevisionPackageDB, ValidatedStoryPackageDB
)

# Import API routes
from backend.api.routes import ingest, pipeline, stories, audit, connectors
from backend.validation_export.api import router as validation_router
from backend.api.middleware import RequestLoggingMiddleware
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="BA Accelerator API",
    description="AI-Powered Requirement-to-User-Story Generation System",
    version="1.0.0"
)

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include API routers
app.include_router(ingest.router)
app.include_router(pipeline.router)
app.include_router(stories.router)
app.include_router(audit.router)
app.include_router(validation_router)
app.include_router(connectors.router)

@app.on_event("startup")
async def on_startup():
    """
    FastAPI startup hook. Automatically creates database tables.
    """
    logger.info("Initializing database and compiling schemas...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize database tables: {str(e)}")

    try:
        llm_client = LLMClient()
        validation_status = await llm_client.validate_provider_keys()
        logger.info("LLM provider validation status: %s", validation_status)
    except Exception as e:
        logger.warning("LLM provider validation failed during startup: %s", e)

@app.get("/", response_class=HTMLResponse, tags=["Root"])
def root():
    """
    Serves the premium single-page backend test client.
    """
    client_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_client.html")
    with open(client_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.post("/save-text-only", tags=["Testing"])
async def save_text_only(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Saves pasted text to a temporary file and returns its path.
    Does NOT trigger any pipeline execution.
    """
    text_content = payload.get("text", "")
    import tempfile
    import uuid
    job_id = str(uuid.uuid4())
    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(base_dir, "data", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    temp_file_path = os.path.join(upload_dir, f"{job_id}_pasted_brd.txt")
    with open(temp_file_path, "w", encoding="utf-8") as f:
        f.write(text_content)
    return {
        "job_id": job_id,
        "file_path": temp_file_path
    }

@app.post("/run-from-text", tags=["Testing"])
async def run_from_text(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Helper endpoint for the test client: accepts raw text, writes to a temp file,
    and runs the entire ingestion + pipeline execution flow.
    """
    text_content = payload.get("text", "")
    
    # Write text to a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(text_content)
        temp_file_path = temp_file.name
        
    # Trigger Ingestion
    from backend.api.routes.ingest import ingest_requirements
    from backend.api.schemas import APIIngestRequest
    
    ingest_payload = APIIngestRequest(
        source_type="FILE",
        target_identifier=temp_file_path
    )
    
    ingest_res = await ingest_requirements(payload=ingest_payload, db=db, _auth="authorized")
    
    # Trigger Pipeline Run
    from backend.api.routes.pipeline import run_pipeline
    from backend.api.schemas import PipelineRunRequest
    
    pipeline_payload = PipelineRunRequest(
        job_id=ingest_res.job_id,
        max_retries=3
    )
    
    await run_pipeline(payload=pipeline_payload, db=db, _auth="authorized")
    
    return {
        "job_id": ingest_res.job_id,
        "status": "RUNNING"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Liveness probe. Returns current operational status.
    """
    return {"status": "OK", "version": "1.0.0"}

if __name__ == "__main__":
    # Start ASGI server
    uvicorn.run(
        "backend.main:app", 
        host=settings.HOST or "0.0.0.0", 
        port=settings.PORT or 8000, 
        reload=False
    )

# INTEGRATION NOTE
# Uvicorn loads config ports from global settings.
# FastAPI automatic documentation is accessible at /docs or /redoc.
