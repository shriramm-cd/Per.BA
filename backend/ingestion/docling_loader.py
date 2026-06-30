"""
=== FILE: backend/ingestion/docling_loader.py ===

Async Docling-based document loader.
Supports local file ingestion, remote URL ingestion (via httpx + tempfile),
and a plain-text fallback for .txt files when Docling fails.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

import httpx

from designlab_core.utilities.logger import get_logger, log_error, log_info, log_warning

logger = get_logger("ingestion.docling_loader")

# ── Docling import (lazy) ──────────────────────────────────────────────────────

try:
    from docling.document_converter import DocumentConverter
    from docling.exceptions import ConversionError  # graceful if missing
    _DOCLING_AVAILABLE = True
except Exception as e:
    _DOCLING_AVAILABLE = False
    log_warning(
        f"Docling is not available (failed to import/load: {e}). File/URL extraction will use text fallback only.",
    )



# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_converter() -> "DocumentConverter":
    """Return a lazily-instantiated DocumentConverter (cached per process)."""
    if not _DOCLING_AVAILABLE:
        raise RuntimeError(
            "docling package is not installed. Run: pip install docling"
        )
    # Re-use a module-level singleton to avoid reloading models on every call.
    if _get_converter._instance is None:
        log_info("Initialising Docling DocumentConverter (models may download on first run).")
        _get_converter._instance = DocumentConverter()
    return _get_converter._instance


_get_converter._instance = None  # type: ignore[attr-defined]


def _run_docling_sync(source: str) -> dict[str, Any]:
    """
    Synchronous Docling conversion. Returns {"text": str, "metadata": dict}.
    Runs in a thread via asyncio.to_thread to avoid blocking the event loop.
    """
    converter = _get_converter()
    try:
        result = converter.convert(source)
    except Exception as exc:
        # Attempt to catch DocumentConversionError or any Docling-internal error
        raise RuntimeError(f"Docling conversion failed for '{source}': {exc}") from exc

    markdown: str = result.document.export_to_markdown()

    # Build metadata from Docling result where available
    meta: dict[str, Any] = {}
    try:
        meta["page_count"] = len(result.document.pages) if hasattr(result.document, "pages") else None
        meta["title"] = result.document.title if hasattr(result.document, "title") else None
        meta["docling_version"] = result.document.version if hasattr(result.document, "version") else None
    except Exception:
        pass  # metadata extraction is best-effort

    return {"text": markdown, "metadata": meta}


# ── Public async functions ─────────────────────────────────────────────────────

def _extract_text_from_pdf(path: Path) -> str:
    import pypdf
    reader = pypdf.PdfReader(path)
    text_parts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text_parts.append(t)
    return "\n\n".join(text_parts)

def _extract_text_from_docx(path: Path) -> str:
    import zipfile
    import xml.etree.ElementTree as ET
    text_parts = []
    with zipfile.ZipFile(path) as docx:
        xml_content = docx.read('word/document.xml')
        root = ET.fromstring(xml_content)
        for paragraph in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
            p_text = []
            for text in paragraph.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                if text.text:
                    p_text.append(text.text)
            if p_text:
                text_parts.append("".join(p_text))
    return "\n".join(text_parts)

def _extract_text_from_xlsx(path: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    text_parts = []
    for sheet in wb.worksheets:
        sheet_parts = [f"--- Sheet: {sheet.title} ---"]
        for row in sheet.iter_rows(values_only=True):
            row_text = [str(cell) for cell in row if cell is not None]
            if row_text:
                sheet_parts.append(" | ".join(row_text))
        if len(sheet_parts) > 1:
            text_parts.append("\n".join(sheet_parts))
    return "\n\n".join(text_parts)

async def _extract_text_from_audio(path: Path) -> str:
    from backend.config import settings
    if settings.GROQ_API_KEY:
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            with open(path, "rb") as audio_file:
                transcription = await client.audio.transcriptions.create(
                    file=(path.name, audio_file.read()),
                    model="whisper-large-v3",
                    response_format="text",
                )
            return transcription
        except Exception as e:
            logger.error(f"Groq Whisper transcription failed: {e}")
    return f"[Mock Audio Transcription] Requirements extracted from audio file: {path.name}."

async def _extract_text_from_image(path: Path) -> str:
    from backend.config import settings
    import base64
    if settings.GROQ_API_KEY:
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            with open(path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode("utf-8")
            
            response = await client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Perform OCR on this image. Extract and return ALL text found in this requirement document or screenshot exactly as written. Do not add any introduction, explanations, or markdown code fences."},
                            {
                                  "type": "image_url",
                                  "image_url": {
                                      "url": f"data:image/jpeg;base64,{encoded}"
                                  }
                              }
                        ]
                    }
                ],
                temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq Vision OCR failed: {e}")
    return f"[Mock OCR Extraction] Requirements extracted from image: {path.name}."

def _extract_text_from_email(path: Path) -> str:
    import email
    from email.policy import default
    with open(path, "rb") as f:
        msg = email.message_from_bytes(f.read(), policy=default)
    
    subject = msg.get('subject', '')
    from_addr = msg.get('from', '')
    to_addr = msg.get('to', '')
    
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get_content_disposition())
            if content_type == "text/plain" and "attachment" not in content_disposition:
                body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                break
    else:
        body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')
        
    headers = []
    if subject:
        headers.append(f"Subject: {subject}")
    if from_addr:
        headers.append(f"From: {from_addr}")
    if to_addr:
        headers.append(f"To: {to_addr}")
        
    return "\n".join(headers) + "\n\n" + body


def _extract_text_from_csv(path: Path) -> str:
    import csv
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                rows.append(" | ".join(row))
    return "\n".join(rows)

async def load_from_file(file_path: str) -> dict[str, Any]:
    """
    Load and extract text from a local file using Docling or custom fallbacks.

    Args:
        file_path: Absolute or relative path to the document.

    Returns:
        {"text": str, "metadata": dict}

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If all extraction methods fail.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    log_info("load_from_file called", context={"path": file_path})

    # ── Custom Extractor Routing ──────────────────────────────────────────────
    suffix = path.suffix.lower()
    supported_extensions = [".pdf", ".docx", ".xlsx", ".txt", ".wav", ".mp3", ".m4a", ".png", ".jpg", ".jpeg", ".eml", ".csv"]
    if not _DOCLING_AVAILABLE or suffix in supported_extensions:
        try:
            if suffix == ".txt":
                text = path.read_text(encoding="utf-8", errors="replace")
                method = "txt_read"
            elif suffix == ".pdf":
                text = await asyncio.to_thread(_extract_text_from_pdf, path)
                method = "pypdf"
            elif suffix == ".docx":
                text = await asyncio.to_thread(_extract_text_from_docx, path)
                method = "xml_docx"
            elif suffix == ".xlsx":
                text = await asyncio.to_thread(_extract_text_from_xlsx, path)
                method = "openpyxl"
            elif suffix in [".wav", ".mp3", ".m4a"]:
                text = await _extract_text_from_audio(path)
                method = "whisper_audio"
            elif suffix in [".png", ".jpg", ".jpeg"]:
                text = await _extract_text_from_image(path)
                method = "vision_ocr"
            elif suffix == ".eml":
                text = await asyncio.to_thread(_extract_text_from_email, path)
                method = "email_parser"
            elif suffix == ".csv":
                text = await asyncio.to_thread(_extract_text_from_csv, path)
                method = "csv_parser"
            else:
                text = path.read_text(encoding="utf-8", errors="replace")
                method = "text_fallback"
                
            log_info(f"Custom extractor ({method}) used for {suffix} file.")
            return {
                "text": text,
                "metadata": {
                    "file_name": path.name,
                    "file_path": str(path),
                    "extraction_method": method,
                    "source": method,
                },
            }

        except Exception as exc:
            log_warning(f"Custom extractor failed for {file_path}: {exc}. Trying Docling...")


    # ── Docling extraction ────────────────────────────────────────────────────
    try:
        result = await asyncio.to_thread(_run_docling_sync, str(path))
        result["metadata"]["file_name"] = path.name
        result["metadata"]["file_path"] = str(path)
        result["metadata"]["extraction_method"] = "docling"
        log_info("Docling extraction succeeded.", context={"file": path.name})
        return result
    except RuntimeError as exc:
        # Last-resort: attempt raw text read
        log_error("Docling extraction failed — attempting raw text fallback.", exc=exc)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            return {
                "text": text,
                "metadata": {
                    "file_name": path.name,
                    "file_path": str(path),
                    "extraction_method": "text_fallback",
                },
            }
        except Exception as fallback_exc:
            raise RuntimeError(
                f"All extraction methods failed for '{file_path}': {fallback_exc}"
            ) from exc



async def load_from_url(url: str) -> dict[str, Any]:
    """
    Download a remote document, save to a temp file, extract via Docling, then clean up.

    Args:
        url: HTTP/HTTPS URL pointing to the document.

    Returns:
        {"text": str, "metadata": dict}

    Raises:
        RuntimeError: On download failure or extraction failure.
    """
    log_info("load_from_url called", context={"url": url})

    tmp_path: str | None = None
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        # Derive a safe extension from the content-type or URL
        suffix = _infer_suffix(url, content_type)

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, prefix="ingestion_url_"
        ) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        log_info("URL document downloaded to temp file.", context={"tmp": tmp_path})

        result = await load_from_file(tmp_path)
        result["metadata"]["source_url"] = url
        result["metadata"]["content_type"] = content_type
        return result

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"HTTP error downloading '{url}': {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Network error downloading '{url}': {exc}") from exc
    finally:
        # Always clean up the temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                log_info("Temporary download file cleaned up.", context={"tmp": tmp_path})
            except OSError:
                pass


def _infer_suffix(url: str, content_type: str) -> str:
    """Attempt to infer a file extension from the URL path or Content-Type."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path_suffix = Path(parsed.path).suffix
    if path_suffix and len(path_suffix) <= 5:
        return path_suffix

    # Map common MIME types
    mime_map = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "text/html": ".html",
        "text/plain": ".txt",
        "image/png": ".png",
        "image/jpeg": ".jpg",
    }
    for mime, ext in mime_map.items():
        if mime in content_type:
            return ext
    return ".bin"


async def load(ingestion_input: Any) -> dict[str, Any]:
    """
    Route-aware load: dispatches to load_from_file or load_from_url
    based on the IngestionInput fields.

    Args:
        ingestion_input: IngestionInput instance.

    Returns:
        {"text": str, "metadata": dict}
    """
    if ingestion_input.file_path:
        return await load_from_file(ingestion_input.file_path)
    if ingestion_input.url:
        return await load_from_url(ingestion_input.url)
    raise ValueError(
        "load() requires either file_path or url on the IngestionInput."
    )


# ─── INTEGRATION NOTE ─────────────────────────────────────────────────────────
# Produces : {"text": str, "metadata": dict}
# Consumed : ingestion/__init__.py  run_ingestion() for file/url source types
