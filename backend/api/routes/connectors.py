import uuid
import datetime
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.db.postgres import get_db_session, AsyncSessionLocal
from backend.db.models import Job
from backend.ingestion.text_normalizer import TextNormalizer
from backend.ingestion.fingerprint import Fingerprint
from backend.orchestrator.graph import pipeline_graph, reset_pipeline_debug_state

router = APIRouter(prefix="/connectors", tags=["Connectors"])

# Mock Data
MOCK_JIRA_PROJECTS = [
    {"id": "PROJ-HRMS", "name": "Human Resource Management System", "key": "HRMS"},
    {"id": "PROJ-FIN", "name": "Finance & Payroll System", "key": "FIN"},
    {"id": "PROJ-ECOM", "name": "E-Commerce Platform", "key": "ECOM"}
]

MOCK_JIRA_EPICS = {
    "PROJ-HRMS": [
        {"id": "EPIC-LEAVE", "name": "Leave Management Feature", "key": "HRMS-101"},
        {"id": "EPIC-ATTEND", "name": "Attendance & Tracking", "key": "HRMS-102"}
    ],
    "PROJ-FIN": [
        {"id": "EPIC-PAY", "name": "Payroll Processing", "key": "FIN-201"}
    ],
    "PROJ-ECOM": [
        {"id": "EPIC-CART", "name": "Shopping Cart & Checkout", "key": "ECOM-301"}
    ]
}

MOCK_JIRA_STORIES = {
    "EPIC-LEAVE": [
        {"id": "STORY-APPLY", "name": "Apply for Leave Request", "key": "HRMS-110", "description": "As an employee, I want to submit a leave request so that my manager can approve it."},
        {"id": "STORY-APPROVE", "name": "Approve or Reject Leave", "key": "HRMS-111", "description": "As a manager, I want to review leave requests so that I can approve or reject them."}
    ],
    "EPIC-ATTEND": [
        {"id": "STORY-CLOCK", "name": "Clock In/Out", "key": "HRMS-120", "description": "As an employee, I want to clock in and out so that my hours are tracked."}
    ]
}

MOCK_CONFLUENCE_SPACES = [
    {"id": "SPACE-HR", "name": "HR & People Ops", "key": "HR"},
    {"id": "SPACE-ENG", "name": "Engineering Wiki", "key": "ENG"}
]

MOCK_SHAREPOINT_SITES = [
    {"id": "SITE-PORTAL", "name": "Intranet Portal", "url": "https://sharepoint.com/sites/portal"}
]

# Request Schemas
class ConnectorImportRequest(BaseModel):
    source_type: str  # JIRA, CONFLUENCE, SHAREPOINT, GDRIVE
    project_id: Optional[str] = None
    epic_id: Optional[str] = None
    story_id: Optional[str] = None
    space_id: Optional[str] = None
    page_id: Optional[str] = None
    document_id: Optional[str] = None
    gdrive_url: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None

@router.get("/jira/projects")
async def get_jira_projects():
    """
    Returns a list of mock Jira projects.
    """
    return {"projects": MOCK_JIRA_PROJECTS}

@router.get("/jira/epics")
async def get_jira_epics(project_id: str):
    """
    Returns a list of mock Jira epics under a project.
    """
    epics = MOCK_JIRA_EPICS.get(project_id, [])
    return {"epics": epics}

@router.get("/jira/stories")
async def get_jira_stories(epic_id: str):
    """
    Returns a list of mock Jira stories under an epic.
    """
    stories = MOCK_JIRA_STORIES.get(epic_id, [])
    return {"stories": stories}

@router.get("/confluence/spaces")
async def get_confluence_spaces():
    """
    Returns a list of mock Confluence spaces.
    """
    return {"spaces": MOCK_CONFLUENCE_SPACES}

@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_requirements(
    payload: ConnectorImportRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Imports requirements from the selected connector and triggers the pipeline.
    """
    source_type = payload.source_type.upper()
    job_id = str(uuid.uuid4())
    
    # Generate mock requirement text based on selections
    if source_type == "JIRA":
        target = f"Jira Story: {payload.story_id or payload.epic_id or payload.project_id}"
        req_text = (
            f"JIRA IMPORTED REQUIREMENT DOCUMENT\n"
            f"Project: {payload.project_id}\n"
            f"Epic: {payload.epic_id}\n"
            f"Story: {payload.story_id}\n\n"
            f"Functional Requirement: The system must allow users to perform leave actions. "
            f"Employees must be able to submit leave applications with start date, end date, and leave type. "
            f"Managers must receive notifications and be able to approve or reject requests. "
            f"All actions must be logged in the audit history."
        )
    elif source_type == "CONFLUENCE":
        target = f"Confluence Page: {payload.page_id or payload.space_id}"
        req_text = (
            f"CONFLUENCE IMPORTED REQUIREMENT DOCUMENT\n"
            f"Space: {payload.space_id}\n"
            f"Page: {payload.page_id}\n\n"
            f"Functional Requirement: The Leave Management system must support automatic accruals. "
            f"Annual leave accrues at 1.5 days per month. Sick leave accrues at 1 day per month. "
            f"Unused leave rolls over up to a maximum of 30 days."
        )
    elif source_type == "SHAREPOINT":
        target = f"SharePoint Document: {payload.document_id}"
        req_text = (
            f"SHAREPOINT IMPORTED REQUIREMENT DOCUMENT\n"
            f"Document ID: {payload.document_id}\n\n"
            f"Functional Requirement: Leave requests cannot be backdated. "
            f"Requests must be submitted at least 3 business days in advance, except for sick leave. "
            f"A medical certificate is mandatory for sick leave exceeding 3 consecutive days."
        )
    elif source_type == "GDRIVE":
        target = f"Google Drive Link: {payload.gdrive_url}"
        req_text = (
            f"GOOGLE DRIVE IMPORTED REQUIREMENT DOCUMENT\n"
            f"URL: {payload.gdrive_url}\n\n"
            f"Functional Requirement: The system must integrate with Slack. "
            f"Leave approval requests must send a Slack notification to the manager. "
            f"Managers must be able to approve or reject directly from Slack."
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source type '{source_type}'. Use JIRA, CONFLUENCE, SHAREPOINT, or GDRIVE."
        )

    # 1. Create a job record in DB
    job = Job(
        id=job_id,
        status="RUNNING",
        source_type=source_type,
        config=payload.connection_config or {}
    )
    db.add(job)
    await db.commit()

    # 2. Normalize and check fingerprints
    cleaned_text = TextNormalizer.clean(req_text)
    lang = TextNormalizer.detect_language(cleaned_text)
    fingerprint_hash = Fingerprint.calculate(cleaned_text)
    is_duplicate = await Fingerprint.check_and_register(fingerprint_hash, job_id)

    job.meta_info = {
        "fingerprint": fingerprint_hash,
        "language": lang,
        "char_count": len(cleaned_text),
        "target": target,
        "original_filename": f"imported_{source_type.lower()}_{job_id[:8]}.txt"
    }
    await db.commit()

    # 3. Trigger LangGraph pipeline in background
    reset_pipeline_debug_state(job_id)
    
    async def run_in_background():
        try:
            initial_state = {
                "job_id": job_id,
                "source_type": source_type,
                "raw_text": cleaned_text,
                "fingerprint": fingerprint_hash,
                "requirements": [],
                "actors": [],
                "business_rules": [],
                "ambiguities": [],
                "conflicts": [],
                "confidence_score": 0.0,
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
                "user_stories": [],
                "plain_text_summary": "",
                "validation_results": {},
                "quality_score": 0.0,
                "is_approved": False,
                "master_context": {},
                "story_contexts": [],
                "retry_count": 0,
                "max_retries": 3,
                "status": "RUNNING",
                "error_message": None,
                "human_approved": False,
                "approval_status": None,
                "domain_detection": None
            }
            config = {"configurable": {"thread_id": job_id}}
            await pipeline_graph.ainvoke(initial_state, config)
        except Exception as e:
            logger.error(f"Background pipeline execution failed for imported job {job_id}: {str(e)}")
            async with AsyncSessionLocal() as session:
                from sqlalchemy import update
                stmt_fail = update(Job).where(Job.id == job_id).values(status="FAILED", error_message=str(e))
                await session.execute(stmt_fail)
                await session.commit()

    asyncio.create_task(run_in_background())

    return {
        "job_id": job_id,
        "status": "RUNNING",
        "source_type": source_type,
        "target": target,
        "is_duplicate": is_duplicate,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
    }
