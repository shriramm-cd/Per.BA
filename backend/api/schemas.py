from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

class APIIngestRequest(BaseModel):
    source_type: str = Field(..., description="Ingestion type (JIRA, CONFLUENCE, SHAREPOINT, GDRIVE, or FILE)")
    target_identifier: str = Field(..., description="Issue code, page ID, file path, or URL")
    connection_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Auth configuration variables overrides")

class APIIngestResponse(BaseModel):
    job_id: str = Field(..., description="Unique generated transaction job ID")
    fingerprint: str = Field(..., description="Ingested file content checksum")
    is_duplicate: bool = Field(..., description="True if document has been processed previously")
    status: str = Field(..., description="State of the transaction")

class PipelineRunRequest(BaseModel):
    job_id: str = Field(..., description="Target transaction ID to initiate pipeline for")
    max_retries: int = Field(default=3, description="Maximum automated low-confidence iterations")

class PipelineRunResponse(BaseModel):
    job_id: str = Field(..., description="Target job transaction ID")
    status: str = Field(..., description="Initial transition state")

class StoryResponse(BaseModel):
    id: str
    epic: str
    feature: str
    title: str
    user_story: str
    acceptance_criteria: List[Dict[str, Any]]
    trace_mappings: List[str]
    validation_results: Optional[Dict[str, Any]] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    source_type: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class AuditLogResponse(BaseModel):
    id: int
    node_name: str
    status: str
    message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime

# INTEGRATION NOTE
# API schema configurations support documentation generation page under FastAPI (/docs).
