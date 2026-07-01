import os
import uuid
import tempfile
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import APIIngestRequest, APIIngestResponse
from backend.api.middleware import verify_api_key
from backend.db.postgres import get_db_session
from backend.db.models import Job
from backend.ingestion.docling_loader import load_from_file
from backend.ingestion.text_normalizer import TextNormalizer
from backend.ingestion.fingerprint import Fingerprint

# Import connectors
from backend.ingestion.connectors.jira_connector import JiraConnector
from backend.ingestion.connectors.confluence_connector import ConfluenceConnector
from backend.ingestion.connectors.sharepoint_connector import SharePointConnector
from backend.ingestion.connectors.gdrive_connector import GDriveConnector

from backend.shared.logger import get_logger
from backend.agents.domain_detection import DomainDetectionModule
from pydantic import BaseModel
from typing import Optional, Dict, Any

logger = get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["Ingestion"])

@router.post("", response_model=APIIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_requirements(
    payload: APIIngestRequest,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_api_key)
):
    """
    Ingests requirement document text from direct paths or connected sources.
    Calculates fingerprints and initializes pipeline jobs.
    """
    source_type = payload.source_type.upper()
    target = payload.target_identifier
    config_override = payload.connection_config or {}

    logger.info(f"Received Ingest request. Source: {source_type}, Target: {target}")

    # 1. Create a job record in DB
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        status="PENDING",
        source_type=source_type,
        config=config_override
    )
    db.add(job)
    await db.commit()

    raw_text = ""

    try:
        # 2. Retrieve content based on connector selection
        if source_type == "FILE":
            file_res = await load_from_file(target)
            raw_text = file_res.get("text", "") if isinstance(file_res, dict) else file_res

            
        elif source_type == "JIRA":
            conn = JiraConnector(
                server_url=config_override.get("jira_server_url"),
                username=config_override.get("jira_username"),
                api_token=config_override.get("jira_api_token")
            )
            conn.authenticate()
            res = await conn.fetch(target)
            raw_text = res.get("text", "")
            
        elif source_type == "CONFLUENCE":
            conn = ConfluenceConnector(
                server_url=config_override.get("confluence_server_url"),
                username=config_override.get("confluence_username"),
                api_token=config_override.get("confluence_api_token")
            )
            conn.authenticate()
            res = await conn.fetch(target)
            raw_text = res.get("text", "")
            
        elif source_type == "SHAREPOINT":
            conn = SharePointConnector(
                tenant_id=config_override.get("sharepoint_tenant_id"),
                client_id=config_override.get("sharepoint_client_id"),
                client_secret=config_override.get("sharepoint_client_secret"),
                site_id=config_override.get("sharepoint_site_id")
            )
            conn.authenticate()
            res = await conn.fetch(target)
            raw_text = res.get("text", "")
            
        elif source_type == "GDRIVE":
            conn = GDriveConnector(
                credentials_json=config_override.get("gdrive_credentials_json")
            )
            conn.authenticate()
            res = await conn.fetch(target)
            raw_text = res.get("text", "")
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported source type '{source_type}'. Use FILE, JIRA, CONFLUENCE, SHAREPOINT, or GDRIVE."
            )

        # 3. Text clean-up and normalization
        cleaned_text = TextNormalizer.clean(raw_text)
        lang = TextNormalizer.detect_language(cleaned_text)

        # 4. Fingerprint checks
        fingerprint_hash = Fingerprint.calculate(cleaned_text)
        is_duplicate = await Fingerprint.check_and_register(fingerprint_hash, job_id)

        # 5. Persist retrieved text and status to job DB
        job.meta_info = {
            "fingerprint": fingerprint_hash,
            "language": lang,
            "char_count": len(cleaned_text),
            "target": target
        }
        
        # We can temporarily store the text on the job's model or a local S3/MinIO bucket.
        # For simplicity and compliance, store layout directly in a local text file named after the job_id
        # inside a workspace temp folder or on the Job model itself.
        # Let's save to a localized directory: backend/data/requirements/<job_id>.txt
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "requirements")
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, f"{job_id}.txt")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)

        await db.commit()

        return APIIngestResponse(
            job_id=job_id,
            fingerprint=fingerprint_hash,
            is_duplicate=is_duplicate,
            status="PENDING"
        )

    except Exception as e:
        logger.error(f"Failed ingestion flow for target {target}: {str(e)}")
        # Update Job status to fail
        job.status = "FAILED"
        job.error_message = str(e)
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion process failed: {str(e)}"
        )

from fastapi import File, UploadFile
from typing import List
import shutil
import datetime

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_brd(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Uploads BRD or requirement documents (PDF, DOCX, XLSX, TXT),
    saves them to data/uploads/, extracts text, and triggers the pipeline.
    """
    allowed_extensions = {".pdf", ".docx", ".xlsx", ".txt"}
    max_file_size = 10 * 1024 * 1024  # 10MB
    
    results = []
    
    # Create upload directory if it doesn't exist
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    upload_dir = os.path.join(base_dir, "data", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    for file in files:
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        
        # 1. Validate file extension
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Supported formats: PDF, DOCX, XLSX, TXT."
            )
            
        # 2. Validate file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{filename}' exceeds the maximum size of 10MB."
            )
            
        # 3. Create a unique Job ID
        job_id = str(uuid.uuid4())
        
        # 4. Save the file to data/uploads/
        saved_filename = f"{job_id}_{filename}"
        saved_path = os.path.join(upload_dir, saved_filename)
        try:
            with open(saved_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            logger.error(f"Failed to save uploaded file {filename}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save uploaded file: {str(e)}"
            )
            
        # 5. Extract text from the saved file
        try:
            file_res = await load_from_file(saved_path)
            raw_text = file_res.get("text", "") if isinstance(file_res, dict) else file_res
        except Exception as e:
            logger.error(f"Failed to extract text from {filename}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to extract text from '{filename}': {str(e)}"
            )
            
        if not raw_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uploaded file '{filename}' contains no readable text."
            )
            
        try:
            # 6. Clean and normalize
            cleaned_text = TextNormalizer.clean(raw_text)
            lang = TextNormalizer.detect_language(cleaned_text)
            
            # 7. Calculate fingerprint
            fingerprint_hash = Fingerprint.calculate(cleaned_text)
            is_duplicate = await Fingerprint.check_and_register(fingerprint_hash, job_id)
            
            # 8. Create Job in DB
            job = Job(
                id=job_id,
                status="RUNNING",
                source_type="FILE",
                config={"max_retries": 3, "original_filename": filename},
                meta_info={
                    "fingerprint": fingerprint_hash,
                    "language": lang,
                    "char_count": len(cleaned_text),
                    "target": saved_path,
                    "original_filename": filename
                }
            )
            db.add(job)
            
            # 9. Save cleaned text to data/requirements/{job_id}.txt
            req_dir = os.path.join(base_dir, "data", "requirements")
            os.makedirs(req_dir, exist_ok=True)
            req_path = os.path.join(req_dir, f"{job_id}.txt")
            with open(req_path, "w", encoding="utf-8") as f:
                f.write(cleaned_text)
                
            await db.commit()
            
            # 10. Trigger Pipeline in Background
            from backend.orchestrator.graph import pipeline_graph, reset_pipeline_debug_state
            reset_pipeline_debug_state(job_id)
            
            async def run_in_background():
                try:
                    initial_state = {
                        "job_id": job_id,
                        "source_type": "FILE",
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
                    logger.error(f"Background pipeline execution failed for job {job_id}: {str(e)}")
                    from backend.db.postgres import AsyncSessionLocal
                    from sqlalchemy import update
                    async with AsyncSessionLocal() as session:
                        stmt_fail = update(Job).where(Job.id == job_id).values(status="FAILED", error_message=str(e))
                        await session.execute(stmt_fail)
                        await session.commit()
            
            import asyncio
            asyncio.create_task(run_in_background())
            
            results.append({
                "job_id": job_id,
                "filename": filename,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "status": "RUNNING",
                "is_duplicate": is_duplicate
            })
            
        except Exception as e:
            logger.error(f"Failed to process uploaded file {filename}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Processing failed for '{filename}': {str(e)}"
            )
            
    return {"uploaded_files": results}


class IngestPreviewRequest(BaseModel):
    source_type: str  # FILE, JIRA, CONFLUENCE, SHAREPOINT, GDRIVE
    target_identifier: str
    connection_config: Optional[Dict[str, Any]] = None


@router.post("/preview")
async def preview_ingest(
    payload: IngestPreviewRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves and normalizes requirements from a source, running domain detection for an intake preview.
    """
    source_type = payload.source_type.upper()
    target = payload.target_identifier
    config_override = payload.connection_config or {}

    logger.info(f"Previewing Ingestion for Source: {source_type}, Target: {target}")
    raw_text = ""

    try:
        if source_type == "FILE":
            file_res = await load_from_file(target)
            raw_text = file_res.get("text", "") if isinstance(file_res, dict) else file_res
        elif source_type == "JIRA":
            conn = JiraConnector(
                server_url=config_override.get("jira_server_url"),
                username=config_override.get("jira_username"),
                api_token=config_override.get("jira_api_token")
            )
            conn.authenticate()
            res = await conn.fetch(target)
            raw_text = res.get("text", "")
        elif source_type == "CONFLUENCE":
            conn = ConfluenceConnector(
                server_url=config_override.get("confluence_server_url"),
                username=config_override.get("confluence_username"),
                api_token=config_override.get("confluence_api_token")
            )
            conn.authenticate()
            res = await conn.fetch(target)
            raw_text = res.get("text", "")
        elif source_type == "SHAREPOINT":
            conn = SharePointConnector(
                tenant_id=config_override.get("sharepoint_tenant_id"),
                client_id=config_override.get("sharepoint_client_id"),
                client_secret=config_override.get("sharepoint_client_secret"),
                site_id=config_override.get("sharepoint_site_id")
            )
            conn.authenticate()
            res = await conn.fetch(target)
            raw_text = res.get("text", "")
        elif source_type == "GDRIVE":
            conn = GDriveConnector(
                credentials_json=config_override.get("gdrive_credentials_json")
            )
            conn.authenticate()
            res = await conn.fetch(target)
            raw_text = res.get("text", "")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported source type '{source_type}'."
            )

        # Text clean-up and normalization
        cleaned_text = TextNormalizer.clean(raw_text)
        lang = TextNormalizer.detect_language(cleaned_text)
        fingerprint_hash = Fingerprint.calculate(cleaned_text)

        # Domain Detection
        domain_detector = DomainDetectionModule()
        try:
            domain_res = await domain_detector.detect_domain(cleaned_text)
            domain_info = {
                "primary_domain": domain_res.primary_domain,
                "secondary_domains": domain_res.secondary_domains,
                "confidence": domain_res.confidence,
                "reasoning": domain_res.reasoning
            }
        except Exception as e:
            logger.error(f"Domain detection failed during preview: {str(e)}")
            domain_info = {
                "primary_domain": "Unknown",
                "secondary_domains": [],
                "confidence": 0,
                "reasoning": f"Detection failed: {str(e)}"
            }

        return {
            "source_type": source_type,
            "file_name": os.path.basename(target) if source_type == "FILE" else target,
            "file_type": "text/plain" if source_type == "FILE" else "connector/text",
            "domain": domain_info,
            "language": lang,
            "extracted_text_preview": cleaned_text[:1000] + ("..." if len(cleaned_text) > 1000 else ""),
            "requirement_package_preview": {
                "raw_text": cleaned_text,
                "fingerprint": fingerprint_hash
            }
        }
    except Exception as e:
        logger.error(f"Preview failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preview failed: {str(e)}"
        )


