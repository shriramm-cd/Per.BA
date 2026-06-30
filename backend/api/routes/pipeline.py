import os
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.api.schemas import PipelineRunRequest, PipelineRunResponse
from backend.api.middleware import verify_api_key
from backend.db.postgres import AsyncSessionLocal, get_db_session
from backend.db.models import Job
from backend.orchestrator.graph import pipeline_graph, get_pipeline_debug_state, reset_pipeline_debug_state
from backend.shared.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline(
    payload: PipelineRunRequest,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_api_key)
):
    """
    Triggers the multi-agent requirements processing pipeline.
    """
    job_id = payload.job_id
    max_retries = payload.max_retries

    # Check if job exists and has PENDING status
    stmt = select(Job).where(Job.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Ingested Job transaction not found.")

    # Update job state
    job.status = "RUNNING"
    if job.config is None:
        job.config = {}
    job.config["max_retries"] = max_retries
    await db.commit()

    logger.info(f"Triggered pipeline run for job {job_id}.")
    reset_pipeline_debug_state(job_id)
    
    # We trigger the execution asynchronously. In a real system, we might push to Celery/Redis queue.
    # Here, we initiate it directly in background tasks or let the user monitor via the stream route.
    # To start the pipeline and return immediately, we can run it in a background task.
    async def run_in_background():
        try:
            # Read requirements text saved during ingestion
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "requirements")
            file_path = os.path.join(data_dir, f"{job_id}.txt")
            
            with open(file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            initial_state = {
                "job_id": job_id,
                "source_type": job.source_type,
                "raw_text": raw_text,
                "fingerprint": job.meta_info.get("fingerprint", "") if job.meta_info else "",
                # Agent 1 outputs
                "requirements": [],
                "actors": [],
                "business_rules": [],
                "ambiguities": [],
                "conflicts": [],
                "confidence_score": 0.0,
                # Agent 2 outputs
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
                # Agent 3 outputs
                "user_stories": [],
                "plain_text_summary": "",
                # Agent 4 outputs
                "validation_results": {},
                "quality_score": 0.0,
                "is_approved": False,
                # Orchestrator outputs
                "master_context": {},
                "story_contexts": [],
                # Execution tracing
                "retry_count": 0,
                "max_retries": max_retries,
                "status": "RUNNING",
                "error_message": None,
                "human_approved": False,
                "approval_status": None
            }

            config = {"configurable": {"thread_id": job_id}}
            # Run the compiled StateGraph
            await pipeline_graph.ainvoke(initial_state, config)
            
        except Exception as e:
            logger.error(f"Background pipeline execution failed for job {job_id}: {str(e)}")
            async with AsyncSessionLocal() as session:
                stmt_fail = update(Job).where(Job.id == job_id).values(status="FAILED", error_message=str(e))
                await session.execute(stmt_fail)
                await session.commit()

    # Launch task in event loop background
    asyncio.create_task(run_in_background())

    return PipelineRunResponse(job_id=job_id, status="RUNNING")


@router.get("/debug/{job_id}")
async def get_pipeline_debug(job_id: str, _auth: str = Depends(verify_api_key)):
    """
    Returns temporary debug state for the requested pipeline job.
    """
    return get_pipeline_debug_state(job_id)


@router.get("/stream/{job_id}")
async def stream_pipeline_progress(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_api_key)
):
    """
    Server-Sent Events (SSE) streaming progress of agent node execution states.
    """
    logger.info(f"SSE connection established for monitoring job {job_id}")
    
    # Verify job existence
    stmt = select(Job).where(Job.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job transaction not found.")

    async def sse_generator():
        # Read raw requirement source text
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "requirements")
        file_path = os.path.join(data_dir, f"{job_id}.txt")
        
        if not os.path.exists(file_path):
            yield f"data: {json.dumps({'error': 'Source requirement file missing.'})}\n\n"
            return

        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        initial_state = {
            "job_id": job_id,
            "source_type": job.source_type,
            "raw_text": raw_text,
            "fingerprint": job.meta_info.get("fingerprint", "") if job.meta_info else "",
            # Agent 1 outputs
            "requirements": [],
            "actors": [],
            "business_rules": [],
            "ambiguities": [],
            "conflicts": [],
            "confidence_score": 0.0,
            # Agent 2 outputs
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
            # Agent 3 outputs
            "user_stories": [],
            "plain_text_summary": "",
            # Agent 4 outputs
            "validation_results": {},
            "quality_score": 0.0,
            "is_approved": False,
            # Orchestrator outputs
            "master_context": {},
            "story_contexts": [],
            # Execution tracing
            "retry_count": 0,
            "max_retries": job.config.get("max_retries", 3) if job.config else 3,
            "status": "RUNNING",
            "error_message": None,
            "human_approved": False,
            "approval_status": None
        }

        config = {"configurable": {"thread_id": job_id}}
        
        try:
            # Stream execution steps from compiled LangGraph StateGraph
            async for chunk in pipeline_graph.astream(initial_state, config):
                # chunk is a dictionary mapping NodeName -> NodeOutputs
                for node_name, output in chunk.items():
                    event_data = {
                        "node": node_name,
                        "status": "IN_PROGRESS" if node_name != "export" else "COMPLETED",
                        "summary": f"Completed node {node_name} execution."
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    # Add delay for client readability
                    await asyncio.sleep(0.5)
            
            yield f"data: {json.dumps({'status': 'FINISHED', 'summary': 'Pipeline workflow completed.'})}\n\n"
        except Exception as e:
            logger.error(f"SSE generator error: {str(e)}")
            yield f"data: {json.dumps({'status': 'FAILED', 'error': str(e)})}\n\n"

    from backend.db.postgres import AsyncSessionLocal # local import for safety inside generator
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

# INTEGRATION NOTE
# Clients connect to /pipeline/stream/{job_id} using native EventSource wrappers.
# Keep content type headers configured for text/event-stream.
