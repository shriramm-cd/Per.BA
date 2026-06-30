from datetime import datetime
from typing import Optional, Dict, Any

from backend.orchestrator.graph import pipeline_graph
from backend.db.postgres import AsyncSessionLocal
from backend.db.models import Job
from backend.shared.logger import get_logger

logger = get_logger(__name__)


async def run_pipeline(job_id: str, raw_text: str, fingerprint: str, source_type: str, config: Optional[Dict[str, Any]] = None):
    """Service entrypoint to run the LangGraph pipeline for a single job.

    This function initializes/updates the Job row, constructs the initial
    graph thread configuration and invokes the compiled StateGraph.
    """
    # Ensure job exists and mark running
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import select, update
            stmt = select(Job).where(Job.id == job_id)
            res = await session.execute(stmt)
            job = res.scalars().first()
            if not job:
                job = Job(id=job_id, status="RUNNING", source_type=source_type, created_at=datetime.utcnow())
                session.add(job)
            else:
                await session.execute(update(Job).where(Job.id == job_id).values(status="RUNNING", updated_at=datetime.utcnow()))
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to initialize job {job_id}: {e}")

    # Construct initial thread state - keys must be JSON serializable and match GraphState
    thread = {
        "job_id": job_id,
        "source_type": source_type,
        "raw_text": raw_text,
        "fingerprint": fingerprint,
        "requirement_package": {},
        "agent1_output": {},
        "requirements": [],
        "actors": [],
        "business_rules": [],
        "ambiguities": [],
        "conflicts": [],
        "confidence_score": 0.0,
        "agent2_output": {},
        "epics": [],
        "features": [],
        "hierarchy": [],
        "requirement_mapping": [],
        "epic_hierarchy": [],
        "dependencies": [],
        "priority": [],
        "coverage_report": {},
        "metadata": {},
        "traceability_matrix": [],
        "story_packets": [],
        "retry_count": 0,
        "max_retries": config.get("max_retries", 3) if config else 3,
        "status": "RUNNING",
        "error_message": None
    }

    logger.info(f"Invoking pipeline graph for job {job_id}")
    try:
        # Start the asynchronous invocation; Language-specific API may return a thread handle or final result
        await pipeline_graph.ainvoke(thread)
        logger.info(f"Pipeline graph invocation completed for job {job_id}")
        # Update job status to COMPLETED
        async with AsyncSessionLocal() as session:
            from sqlalchemy import update
            await session.execute(update(Job).where(Job.id == job_id).values(status="COMPLETED", updated_at=datetime.utcnow()))
            await session.commit()
    except Exception as e:
        logger.error(f"Pipeline execution failed for job {job_id}: {e}")
        async with AsyncSessionLocal() as session:
            from sqlalchemy import update
            await session.execute(update(Job).where(Job.id == job_id).values(status="FAILED", error_message=str(e), updated_at=datetime.utcnow()))
            await session.commit()
        raise
