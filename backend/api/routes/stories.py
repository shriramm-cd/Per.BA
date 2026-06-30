import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.api.schemas import StoryResponse
from backend.api.middleware import verify_api_key
from backend.db.postgres import get_db_session
from backend.db.models import Story, Job

# Import exporters
from backend.validation_export.exporters.jira import JiraExporter
from backend.validation_export.exporters.excel import ExcelExporter
from backend.validation_export.exporters.pdf import PDFExporter
from backend.validation_export.exporters.json_exporter import JSONExporter

from backend.shared.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/stories", tags=["Stories"])

@router.get("/{job_id}", response_model=List[StoryResponse])
async def get_stories_by_job(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_api_key)
):
    """
    Retrieves generated user stories and validation checklists for a specific pipeline job.
    """
    logger.info(f"Retrieving user stories for job {job_id}...")
    
    stmt = select(Story).where(Story.job_id == job_id)
    res = await db.execute(stmt)
    stories = res.scalars().all()

    if not stories:
        logger.warning(f"No stories found in DB for job: {job_id}")
        return []

    return [
        StoryResponse(
            id=story.id,
            epic=story.epic,
            feature=story.feature,
            title=story.title,
            user_story=story.user_story,
            acceptance_criteria=story.acceptance_criteria,
            trace_mappings=story.trace_mappings,
            validation_results=story.validation_results
        )
        for story in stories
    ]


@router.post("/{job_id}/export")
async def export_job_stories(
    job_id: str,
    export_format: str = Query(..., description="Target export format: JIRA, EXCEL, PDF, or JSON"),
    project_key: Optional[str] = Query(None, description="Target Project key (e.g. 'PROJ') if exporting to Jira"),
    target_path: Optional[str] = Query(None, description="Absolute local target file path to save output"),
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_api_key)
):
    """
    Triggers exporters to push stories to Jira projects or save them to Excel, PDF, or JSON files.
    """
    logger.info(f"Request to export stories for job {job_id} in {export_format} format.")

    # 1. Fetch stories
    stmt = select(Story).where(Story.job_id == job_id)
    stories_res = await db.execute(stmt)
    stories = stories_res.scalars().all()

    if not stories:
        raise HTTPException(status_code=404, detail="No stories found matching this Job ID.")

    # Convert SQLAlchemy objects to list of serializable dictionaries
    serialized_stories = []
    for s in stories:
        serialized_stories.append({
            "id": s.id,
            "epic_id": s.epic,
            "feature_id": s.feature,
            "title": s.title,
            "user_story_text": s.user_story,
            "acceptance_criteria": s.acceptance_criteria,
            "trace_mappings": s.trace_mappings
        })

    # Fetch Job data to acquire validation checklist info
    job_stmt = select(Job).where(Job.id == job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    
    validation_results = {}
    if job and job.meta_info and "validation_results" in job.meta_info:
        validation_results = job.meta_info["validation_results"]

    # 2. Match target exporter
    fmt = export_format.upper()
    
    # Setup default paths if not supplied
    export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "exports")
    os.makedirs(export_dir, exist_ok=True)

    try:
        if fmt == "JIRA":
            if not project_key:
                raise HTTPException(status_code=400, detail="project_key query parameter is required for Jira exports.")
            exporter = JiraExporter()
            keys = await exporter.export_stories(project_key, serialized_stories)
            return {"status": "SUCCESS", "message": f"Exported {len(keys)} stories to Jira project {project_key}.", "keys": keys}

        elif fmt == "EXCEL":
            path = target_path or os.path.join(export_dir, f"stories_{job_id}.xlsx")
            exporter = ExcelExporter()
            await exporter.export(serialized_stories, path)
            # If path is local default, return file download response
            if not target_path:
                return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=f"stories_{job_id}.xlsx")
            return {"status": "SUCCESS", "message": f"Excel worksheet created at {path}."}

        elif fmt == "PDF":
            path = target_path or os.path.join(export_dir, f"report_{job_id}.pdf")
            exporter = PDFExporter()
            await exporter.export(serialized_stories, validation_results, path)
            if not target_path:
                return FileResponse(path, media_type="application/pdf", filename=f"report_{job_id}.pdf")
            return {"status": "SUCCESS", "message": f"PDF report compiled at {path}."}

        elif fmt == "JSON":
            path = target_path or os.path.join(export_dir, f"export_{job_id}.json")
            exporter = JSONExporter()
            await exporter.export(serialized_stories, validation_results, path)
            if not target_path:
                return FileResponse(path, media_type="application/json", filename=f"stories_{job_id}.json")
            return {"status": "SUCCESS", "message": f"JSON state dumped to {path}."}

        else:
            raise HTTPException(status_code=400, detail=f"Invalid format '{export_format}'. Use JIRA, EXCEL, PDF, or JSON.")
            
    except Exception as e:
        logger.error(f"Exporter triggered validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export transaction failed: {str(e)}")

# INTEGRATION NOTE
# In local environments, exported PDF/Excel files are saved inside backend/data/exports directory.
