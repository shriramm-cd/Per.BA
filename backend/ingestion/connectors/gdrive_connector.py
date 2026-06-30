"""
=== FILE: backend/ingestion/connectors/gdrive_connector.py ===

Google Drive connector.

  - Service account credentials (JSON file path or inline JSON string)
  - Drive API v3 — export Google Docs as plaintext, download other files
  - Saves binary files to tempfile and extracts text via Docling
  - Health-check via files().list()
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import tempfile
from typing import Any

from designlab_core.utilities.env import get_env
from designlab_core.utilities.logger import get_logger, log_error, log_info, log_warning

from backend.shared.exceptions import ConnectorAuthError
from .base_connector import BaseConnector

logger = get_logger("ingestion.connectors.gdrive")

_GDRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Mime types that are Google Workspace native documents (need export)
_GOOGLE_NATIVE_MIME_TYPES: dict[str, str] = {
    "application/vnd.google-apps.document":     "text/plain",
    "application/vnd.google-apps.spreadsheet":  "text/csv",
    "application/vnd.google-apps.presentation": "application/pdf",
}


class GDriveConnector(BaseConnector):
    """
    Fetches documents from Google Drive using a service account.
    """

    def __init__(self, credentials_json: str | None = None) -> None:
        env = get_env()
        self._credentials_json: str = (
            credentials_json
            or env.model_extra.get("gdrive_service_account_json")
            or env.model_extra.get("GDRIVE_SERVICE_ACCOUNT_JSON")
            or ""
        )
        self._service: Any = None  # googleapiclient Resource

    # ── authenticate ──────────────────────────────────────────────────────────

    def authenticate(self) -> None:
        """
        Build the Google Drive API service using service account credentials.
        Supports both a path to a JSON file and an inline JSON string.
        Raises ConnectorAuthError on failure.
        """
        if not self._credentials_json:
            raise ConnectorAuthError(
                "Google Drive credentials not set. "
                "Set GDRIVE_SERVICE_ACCOUNT_JSON in your .env file "
                "(either a file path or the raw JSON content)."
            )

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            def _build_service() -> Any:
                creds_str = self._credentials_json.strip()
                if creds_str.endswith(".json") and os.path.isfile(creds_str):
                    # Path to JSON key file
                    creds = service_account.Credentials.from_service_account_file(
                        creds_str,
                        scopes=_GDRIVE_SCOPES,
                    )
                else:
                    # Inline JSON string
                    try:
                        info = json.loads(creds_str)
                    except json.JSONDecodeError as exc:
                        raise ConnectorAuthError(
                            f"GDRIVE_SERVICE_ACCOUNT_JSON is neither a valid file path "
                            f"nor valid JSON: {exc}"
                        ) from exc
                    creds = service_account.Credentials.from_service_account_info(
                        info,
                        scopes=_GDRIVE_SCOPES,
                    )
                return build("drive", "v3", credentials=creds, cache_discovery=False)

            import asyncio as _asyncio
            try:
                loop = _asyncio.get_running_loop()
                is_running = loop.is_running()
            except RuntimeError:
                is_running = False

            if is_running:
                # We're inside an async context — defer to thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(_build_service)
                    self._service = future.result(timeout=30)
            else:
                self._service = _build_service()

            log_info("Google Drive authentication successful.")
        except ConnectorAuthError:
            raise
        except Exception as exc:
            raise ConnectorAuthError(
                f"Google Drive authentication failed: {exc}"
            ) from exc

    # ── fetch ─────────────────────────────────────────────────────────────────

    async def fetch(  # type: ignore[override]
        self,
        file_id: str,
    ) -> dict[str, Any]:
        """
        Download or export a Google Drive file and extract its text.

        - Google Docs / Sheets / Slides: exported via files().export_media()
        - Other files: downloaded via files().get_media()
        - Binary (non-UTF-8) files: processed by Docling via a temp file.

        Args:
            file_id: Google Drive file ID.

        Returns:
            {"text": str, "metadata": dict}
        """
        if self._service is None:
            raise ConnectorAuthError(
                "Google Drive service not initialised. Call authenticate() first."
            )

        log_info("Fetching Google Drive file.", context={"file_id": file_id})

        def _download_sync() -> tuple[bytes, dict[str, Any]]:
            from googleapiclient.http import MediaIoBaseDownload

            # 1. Fetch file metadata
            file_meta: dict[str, Any] = (
                self._service.files()
                .get(fileId=file_id, fields="id,name,mimeType,size,createdTime,modifiedTime")
                .execute()
            )
            mime_type: str = file_meta.get("mimeType", "")
            file_name: str = file_meta.get("name", "untitled")

            # 2. Build the appropriate request
            if mime_type in _GOOGLE_NATIVE_MIME_TYPES:
                export_mime = _GOOGLE_NATIVE_MIME_TYPES[mime_type]
                request = self._service.files().export_media(
                    fileId=file_id,
                    mimeType=export_mime,
                )
            else:
                request = self._service.files().get_media(fileId=file_id)

            # 3. Download in chunks
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request, chunksize=1024 * 1024)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            return buffer.getvalue(), file_meta

        raw_bytes, file_meta = await asyncio.to_thread(_download_sync)
        mime_type = file_meta.get("mimeType", "")
        file_name = file_meta.get("name", "untitled")

        # Determine export mime to derive file extension
        export_mime = _GOOGLE_NATIVE_MIME_TYPES.get(mime_type, mime_type)

        # Attempt to decode as plain text first (for exported Docs / Sheets)
        if "text/plain" in export_mime or "text/csv" in export_mime:
            try:
                text = raw_bytes.decode("utf-8", errors="replace")
                metadata = _build_metadata(file_id, file_name, mime_type, file_meta, "gdrive_text_export")
                log_info(
                    "Google Drive file exported as plain text.",
                    context={"file_id": file_id, "file": file_name},
                )
                return {"text": text, "metadata": metadata}
            except Exception:
                pass

        # Otherwise write to tempfile and use Docling
        suffix = _mime_to_ext(mime_type, export_mime, file_name)
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, prefix="gdrive_"
            ) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name

            from ..docling_loader import load_from_file
            extraction = await load_from_file(tmp_path)
            text = extraction.get("text", "")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        metadata = _build_metadata(file_id, file_name, mime_type, file_meta, "docling")
        log_info(
            "Google Drive file extracted via Docling.",
            context={"file_id": file_id, "file": file_name, "chars": len(text)},
        )
        return {"text": text, "metadata": metadata}

    # ── health_check ──────────────────────────────────────────────────────────

    async def health_check(self) -> bool:  # type: ignore[override]
        """
        Verify the Drive API connection by listing a single file.

        Returns:
            True if healthy, False otherwise.
        """
        if self._service is None:
            return False
        try:
            def _ping() -> None:
                self._service.files().list(pageSize=1, fields="files(id)").execute()

            await asyncio.to_thread(_ping)
            log_info("Google Drive health check passed.")
            return True
        except Exception as exc:
            log_warning(f"Google Drive health check failed: {exc}")
            return False

    # ── list_files ────────────────────────────────────────────────────────────

    async def list_files(
        self,
        folder_id: str | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """
        List files in the service-account's Drive (or a specific folder).

        Args:
            folder_id:   Optional parent folder ID to filter results.
            max_results: Maximum number of files to return.

        Returns:
            List of file metadata dicts.
        """
        if self._service is None:
            raise ConnectorAuthError("Google Drive service not initialised.")

        query = f"'{folder_id}' in parents" if folder_id else None

        def _list() -> list[dict[str, Any]]:
            kw: dict[str, Any] = {
                "pageSize": max_results,
                "fields": "files(id,name,mimeType,size,modifiedTime)",
            }
            if query:
                kw["q"] = query
            return self._service.files().list(**kw).execute().get("files", [])

        files = await asyncio.to_thread(_list)
        log_info(f"Listed {len(files)} files from Google Drive.")
        return files


# ── Private helpers ────────────────────────────────────────────────────────────

def _build_metadata(
    file_id: str,
    file_name: str,
    mime_type: str,
    file_meta: dict[str, Any],
    extraction_method: str,
) -> dict[str, Any]:
    return {
        "file_id":           file_id,
        "file_name":         file_name,
        "mime_type":         mime_type,
        "size_bytes":        file_meta.get("size"),
        "created_time":      file_meta.get("createdTime"),
        "modified_time":     file_meta.get("modifiedTime"),
        "extraction_method": extraction_method,
        "source":            "gdrive",
    }


def _mime_to_ext(mime_type: str, export_mime: str, file_name: str) -> str:
    """Derive a file extension for the temp file."""
    if "." in file_name:
        return f".{file_name.rsplit('.', 1)[-1]}"
    _map = {
        "application/pdf":    ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "text/plain":         ".txt",
        "text/csv":           ".csv",
        "image/png":          ".png",
        "image/jpeg":         ".jpg",
    }
    return _map.get(export_mime, _map.get(mime_type, ".bin"))


# ─── INTEGRATION NOTE ─────────────────────────────────────────────────────────
# Produces : {"text": str, "metadata": dict}  (from fetch())
# Consumed : ingestion/__init__.py  run_ingestion() for source_type == "gdrive"
