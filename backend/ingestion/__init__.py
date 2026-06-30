"""
=== FILE: backend/ingestion/__init__.py ===

Public entry point for the Ingestion Module.

Exposes ONLY:
    async def run_ingestion(input: IngestionInput, redis_client=None) -> IngestionOutput

Pipeline flow
─────────────
1.  Route source → connector or Docling loader
2.  Extract raw text + source metadata
3.  Normalize text (NFKC, boilerplate removal, whitespace)
4.  Detect language (langdetect)
5.  Chunk text (512 chars, 50 char overlap)
6.  Generate SHA-256 fingerprint
7.  Deduplicate via Redis (async, fail-open)
8.  Register fingerprint in Redis (if not duplicate)
9.  Build IngestionOutput
10. validate_output() — raises ValueError on schema violation
11. Return validated IngestionOutput

Integration contract
────────────────────
    from ingestion import run_ingestion

    output: IngestionOutput = await run_ingestion(input, redis_client)
    # GraphState.ingestion_output = output
    # Agent 1 reads: GraphState.ingestion_output.text
"""

from __future__ import annotations

import json
from typing import Any

from designlab_core.evaluation.validator import ValidationResult, validate_output
from designlab_core.utilities.logger import get_logger, log_error, log_info, log_warning

from .schemas import IngestionInput, IngestionOutput, SourceType
from .docling_loader import load as _docling_load
from .text_normalizer import normalize, detect_language, chunk_text
from .fingerprint import (
    generate_fingerprint,
    is_duplicate_async,
    register_fingerprint_async,
)

logger = get_logger("ingestion.__init__")


# ── Source routing ─────────────────────────────────────────────────────────────

async def _route_source(inp: IngestionInput) -> dict[str, Any]:
    """
    Dispatch to the appropriate connector or Docling loader based on source_type.
    Returns {"text": str, "metadata": dict, "extraction_method": str}.
    """

    st = inp.source_type

    # ── FILE / URL sources — use Docling ──────────────────────────────────────
    if st in (
        SourceType.pdf, SourceType.docx, SourceType.pptx,
        SourceType.xlsx, SourceType.image, SourceType.html,
        SourceType.txt, SourceType.email, SourceType.url,
    ):
        result = await _docling_load(inp)
        result.setdefault("extraction_method", "docling")
        return result

    # ── JIRA ──────────────────────────────────────────────────────────────────
    if st == SourceType.jira:
        from .connectors.jira_connector import JiraConnector
        connector = JiraConnector()
        connector.authenticate()
        result = await connector.fetch(
            issue_key=inp.jira_issue_key,  # type: ignore[arg-type]
            attachment_name=inp.jira_attachment_name,
        )
        result["extraction_method"] = "jira_api"
        return result

    # ── CONFLUENCE ────────────────────────────────────────────────────────────
    if st == SourceType.confluence:
        from .connectors.confluence_connector import ConfluenceConnector
        connector = ConfluenceConnector()
        connector.authenticate()
        result = await connector.fetch(
            page_id=inp.confluence_page_id,  # type: ignore[arg-type]
        )
        result["extraction_method"] = "confluence_api"
        return result

    # ── SHAREPOINT ────────────────────────────────────────────────────────────
    if st == SourceType.sharepoint:
        from .connectors.sharepoint_connector import SharePointConnector
        connector = SharePointConnector()
        connector.authenticate()
        result = await connector.fetch(
            file_path=inp.sharepoint_file_path,  # type: ignore[arg-type]
            site_id=inp.sharepoint_site_id,
        )
        result["extraction_method"] = "sharepoint_graph_api"
        return result

    # ── GDRIVE ────────────────────────────────────────────────────────────────
    if st == SourceType.gdrive:
        from .connectors.gdrive_connector import GDriveConnector
        connector = GDriveConnector()
        connector.authenticate()
        result = await connector.fetch(
            file_id=inp.gdrive_file_id,  # type: ignore[arg-type]
        )
        result["extraction_method"] = "gdrive_api"
        return result

    raise ValueError(f"Unknown source_type: {st!r}")


# ── Main entrypoint ────────────────────────────────────────────────────────────

async def run_ingestion(
    input: IngestionInput,
    redis_client: Any = None,
) -> IngestionOutput:
    """
    Execute the full ingestion pipeline for a single document source.

    Args:
        input:        Validated IngestionInput describing the source.
        redis_client: Optional redis.asyncio.Redis client for deduplication.
                      If None, dedup is skipped (non-fatal).

    Returns:
        Validated IngestionOutput.

    Raises:
        ValueError: If the built IngestionOutput fails schema validation.
        RuntimeError / ConnectorAuthError: On extraction failures.
    """
    log_info(
        "run_ingestion started.",
        context={"source_type": input.source_type, "jira_key": input.jira_issue_key},
    )

    # ── 1–2. Route + Extract ──────────────────────────────────────────────────
    raw = await _route_source(input)
    raw_text: str           = raw.get("text", "")
    source_meta: dict       = raw.get("metadata", {})
    extraction_method: str  = raw.get("extraction_method", "unknown")

    # Merge caller-supplied metadata
    merged_meta = {**source_meta, **input.metadata}

    # ── 3. Normalize ──────────────────────────────────────────────────────────
    clean_text = normalize(raw_text)

    if not clean_text:
        log_warning("Normalised text is empty — using raw text as fallback.")
        clean_text = raw_text.strip() or "NO_CONTENT_EXTRACTED"

    # ── 4. Detect language ────────────────────────────────────────────────────
    language = detect_language(clean_text)

    # ── 5. Chunk ──────────────────────────────────────────────────────────────
    chunks = chunk_text(clean_text, chunk_size=512, overlap=50)
    # Guarantee at least one non-empty chunk
    if not chunks or all(not c.strip() for c in chunks):
        chunks = [clean_text]

    # ── 6. Fingerprint ────────────────────────────────────────────────────────
    fingerprint = generate_fingerprint(clean_text)

    # ── 7. Dedup ──────────────────────────────────────────────────────────────
    is_dup = await is_duplicate_async(fingerprint, redis_client)

    # ── 8. Register fingerprint (if new) ──────────────────────────────────────
    if not is_dup:
        await register_fingerprint_async(fingerprint, redis_client)
    else:
        log_warning(
            "Duplicate document detected — fingerprint already registered.",
            context={"fingerprint": fingerprint[:16] + "…"},
        )

    # ── 9. Build IngestionOutput ──────────────────────────────────────────────
    output = IngestionOutput(
        # BaseAcceleratorOutput fields
        confidence_score=1.0,
        raw_context=raw_text[:2000],  # first 2000 chars as raw context
        # IngestionOutput fields
        text=clean_text,
        raw_text=raw_text,
        chunks=chunks,
        metadata=merged_meta,
        fingerprint=fingerprint,
        is_duplicate=is_dup,
        language=language,
        source_type=input.source_type.value,
        chunk_count=len(chunks),
        char_count=len(clean_text),
        extraction_method=extraction_method,
    )

    # ── 10. Validate ──────────────────────────────────────────────────────────
    result: ValidationResult = validate_output(
        output.model_dump_json(),
        IngestionOutput,
    )

    if not result.is_valid:
        error_summary = "; ".join(result.errors)
        log_error(
            "IngestionOutput validation failed.",
            context={"errors": error_summary},
        )
        raise ValueError(
            f"IngestionOutput failed schema validation: {error_summary}"
        )

    log_info(
        "run_ingestion completed successfully.",
        context={
            "source_type":        output.source_type,
            "char_count":         output.char_count,
            "chunk_count":        output.chunk_count,
            "language":           output.language,
            "is_duplicate":       output.is_duplicate,
            "extraction_method":  output.extraction_method,
        },
    )

    # ── 11. Return ────────────────────────────────────────────────────────────
    return output


# ── Public exports ─────────────────────────────────────────────────────────────
__all__ = ["run_ingestion", "IngestionInput", "IngestionOutput"]


# ─── INTEGRATION NOTE ─────────────────────────────────────────────────────────
# Produces : IngestionOutput (validated)
# Consumed : Orchestrator sets GraphState.ingestion_output = output
#            Agent 1 reads  GraphState.ingestion_output.text
