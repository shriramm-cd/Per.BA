"""
=== FILE: backend/ingestion/schemas.py ===

Pydantic schemas for the Ingestion Module.
Defines IngestionInput (routing contract) and IngestionOutput (pipeline output).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, model_validator

from designlab_core.schemas.base_schema import BaseAcceleratorOutput

# ── Logger ────────────────────────────────────────────────────────────────────
from designlab_core.utilities.logger import get_logger

logger = get_logger("ingestion.schemas")


# ── Source Type Enum ──────────────────────────────────────────────────────────

class SourceType(str, Enum):
    pdf         = "pdf"
    docx        = "docx"
    pptx        = "pptx"
    xlsx        = "xlsx"
    image       = "image"
    html        = "html"
    txt         = "txt"
    email       = "email"
    jira        = "jira"
    confluence  = "confluence"
    sharepoint  = "sharepoint"
    gdrive      = "gdrive"
    url         = "url"


# ── Input Schema ──────────────────────────────────────────────────────────────

class IngestionInput(BaseAcceleratorOutput):
    """
    Routing contract for all ingestion sources.
    At least one of the location fields must be supplied.
    """

    source_type: SourceType = Field(
        ...,
        description="Source system type.",
    )
    file_path: str | None = Field(
        default=None,
        description="Absolute local path to a document file.",
    )
    url: str | None = Field(
        default=None,
        description="Remote URL to download and ingest.",
    )
    jira_issue_key: str | None = Field(
        default=None,
        description="Jira issue key, e.g. 'PROJ-123'.",
    )
    jira_attachment_name: str | None = Field(
        default=None,
        description="Name of a specific Jira attachment to process (optional).",
    )
    confluence_page_id: str | None = Field(
        default=None,
        description="Confluence page ID.",
    )
    sharepoint_site_id: str | None = Field(
        default=None,
        description="SharePoint site ID.",
    )
    sharepoint_file_path: str | None = Field(
        default=None,
        description="Graph API drive item path for the SharePoint file.",
    )
    gdrive_file_id: str | None = Field(
        default=None,
        description="Google Drive file ID.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional caller-supplied metadata to merge into output.",
    )

    # IngestionInput re-uses BaseAcceleratorOutput fields but supplies defaults
    # so callers don't have to set them.
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    raw_context: str = Field(default="")

    @model_validator(mode="after")
    def _at_least_one_location(self) -> "IngestionInput":
        location_fields = (
            self.file_path,
            self.url,
            self.jira_issue_key,
            self.confluence_page_id,
            self.sharepoint_file_path,
            self.gdrive_file_id,
        )
        if not any(location_fields):
            raise ValueError(
                "IngestionInput requires at least one of: file_path, url, "
                "jira_issue_key, confluence_page_id, sharepoint_file_path, "
                "gdrive_file_id."
            )
        return self


# ── Output Schema ─────────────────────────────────────────────────────────────

class IngestionOutput(BaseAcceleratorOutput):
    """
    Validated output produced by run_ingestion().
    Inherits generated_at, confidence_score, raw_context from BaseAcceleratorOutput.
    """

    text: str = Field(
        ...,
        description="Clean, normalised full text extracted from the source.",
    )
    raw_text: str = Field(
        default="",
        description="Original raw extracted text before normalization.",
    )
    chunks: list[str] = Field(
        ...,
        description="Text split into overlapping chunks ready for embedding.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Source metadata (connector-specific).",
    )
    fingerprint: str = Field(
        ...,
        description="SHA-256 hex digest of the normalised text.",
    )
    is_duplicate: bool = Field(
        default=False,
        description="True when the fingerprint already existed in Redis.",
    )
    language: str = Field(
        ...,
        description="ISO 639-1 language code detected by langdetect, or 'unknown'.",
    )
    source_type: str = Field(
        ...,
        description="SourceType enum value as a string.",
    )
    chunk_count: int = Field(
        ...,
        description="Number of chunks produced.",
    )
    char_count: int = Field(
        ...,
        description="Total character count of the clean text.",
    )
    extraction_method: str = Field(
        ...,
        description="Method used for extraction, e.g. 'docling', 'jira_api', 'confluence_api'.",
    )


# ─── INTEGRATION NOTE ─────────────────────────────────────────────────────────
# Produces : IngestionInput  — validated by run_ingestion() entrypoint
#            IngestionOutput — returned by run_ingestion() to Orchestrator
# Consumed : __init__.run_ingestion() builds IngestionOutput
#            Orchestrator sets GraphState.ingestion_output = IngestionOutput
#            Agent 1 reads GraphState.ingestion_output.text
