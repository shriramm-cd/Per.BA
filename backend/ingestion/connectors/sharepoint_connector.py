"""
=== FILE: backend/ingestion/connectors/sharepoint_connector.py ===

SharePoint connector.

  - MSAL client-credentials OAuth (no user interaction)
  - Microsoft Graph API: file metadata + content download
  - Saves binary content to tempfile and extracts text via Docling
  - Health-check via Graph /me or /sites endpoint
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any

import httpx
import msal

from designlab_core.utilities.env import get_env
from designlab_core.utilities.logger import get_logger, log_error, log_info, log_warning

from backend.shared.exceptions import ConnectorAuthError
from .base_connector import BaseConnector

logger = get_logger("ingestion.connectors.sharepoint")

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class SharePointConnector(BaseConnector):
    """
    Downloads files from Microsoft SharePoint via Microsoft Graph API.
    Uses MSAL client-credentials for authentication (daemon / service-to-service).
    """

    def __init__(
        self,
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        site_id: str | None = None,
    ) -> None:
        env = get_env()
        self._tenant_id: str = (
            tenant_id
            or env.model_extra.get("sharepoint_tenant_id")
            or env.model_extra.get("SHAREPOINT_TENANT_ID")
            or ""
        )
        self._client_id: str = (
            client_id
            or env.model_extra.get("sharepoint_client_id")
            or env.model_extra.get("SHAREPOINT_CLIENT_ID")
            or ""
        )
        self._client_secret: str = (
            client_secret
            or env.model_extra.get("sharepoint_client_secret")
            or env.model_extra.get("SHAREPOINT_CLIENT_SECRET")
            or ""
        )
        self._site_id: str = (
            site_id
            or env.model_extra.get("sharepoint_site_id")
            or env.model_extra.get("SHAREPOINT_SITE_ID")
            or ""
        )
        self._access_token: str | None = None

    # ── authenticate ──────────────────────────────────────────────────────────

    def authenticate(self) -> None:
        """
        Acquire an OAuth access token via MSAL client-credentials flow.
        Raises ConnectorAuthError on missing credentials or token failure.
        """
        missing = [
            name for name, val in [
                ("SHAREPOINT_TENANT_ID",     self._tenant_id),
                ("SHAREPOINT_CLIENT_ID",     self._client_id),
                ("SHAREPOINT_CLIENT_SECRET", self._client_secret),
            ] if not val
        ]
        if missing:
            raise ConnectorAuthError(
                f"SharePoint credentials incomplete. Missing: {', '.join(missing)}"
            )

        authority = f"https://login.microsoftonline.com/{self._tenant_id}"
        try:
            app = msal.ConfidentialClientApplication(
                client_id=self._client_id,
                client_credential=self._client_secret,
                authority=authority,
            )
            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
        except Exception as exc:
            raise ConnectorAuthError(
                f"MSAL token acquisition raised an exception: {exc}"
            ) from exc

        if "access_token" not in result:
            error       = result.get("error", "unknown_error")
            description = result.get("error_description", "No description.")
            raise ConnectorAuthError(
                f"MSAL token acquisition failed [{error}]: {description}"
            )

        self._access_token = result["access_token"]
        log_info(
            "SharePoint authentication successful.",
            context={"tenant_id": self._tenant_id},
        )

    # ── fetch ─────────────────────────────────────────────────────────────────

    async def fetch(  # type: ignore[override]
        self,
        file_path: str,
        site_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Download a SharePoint file and extract its text using Docling.

        Args:
            file_path: Graph API drive item path or drive-item ID,
                       e.g. "drives/{drive_id}/items/{item_id}" or
                            "sites/{site_id}/drive/root:/{relative_path}".
            site_id:   Override the site_id supplied at construction.

        Returns:
            {"text": str, "metadata": dict}
        """
        if not self._access_token:
            raise ConnectorAuthError(
                "SharePoint access token not available. Call authenticate() first."
            )

        resolved_site_id = site_id or self._site_id
        headers = {"Authorization": f"Bearer {self._access_token}"}

        # Build Graph URL — support both full path and relative path styles
        if file_path.startswith("drives/") or file_path.startswith("sites/"):
            graph_url = f"{_GRAPH_BASE}/{file_path}"
        elif resolved_site_id:
            graph_url = f"{_GRAPH_BASE}/sites/{resolved_site_id}/drive/root:/{file_path}"
        else:
            graph_url = f"{_GRAPH_BASE}/{file_path}"

        log_info("Fetching SharePoint file.", context={"graph_url": graph_url})

        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            # 1. File metadata
            meta_resp = await client.get(graph_url, headers=headers)
            if meta_resp.status_code != 200:
                raise RuntimeError(
                    f"Graph metadata call failed [{meta_resp.status_code}]: {meta_resp.text[:500]}"
                )
            meta: dict[str, Any] = meta_resp.json()
            file_name = meta.get("name", "unknown_file")
            mime_type = meta.get("file", {}).get("mimeType", "")
            size_bytes = meta.get("size", 0)

            # 2. Content download URL
            download_url = meta.get("@microsoft.graph.downloadUrl")
            if not download_url:
                # Fallback: construct the content endpoint
                download_url = f"{graph_url}/content"

            content_resp = await client.get(download_url, headers=headers)
            if content_resp.status_code not in (200, 302):
                raise RuntimeError(
                    f"Graph content download failed [{content_resp.status_code}]: "
                    f"{content_resp.text[:500]}"
                )

        # 3. Save to tempfile and extract via Docling
        suffix = f".{file_name.rsplit('.', 1)[-1]}" if "." in file_name else ".bin"
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, prefix="sharepoint_"
            ) as tmp:
                tmp.write(content_resp.content)
                tmp_path = tmp.name

            from ..docling_loader import load_from_file
            extraction = await load_from_file(tmp_path)
            text = extraction.get("text", "")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        metadata: dict[str, Any] = {
            "file_name":       file_name,
            "file_path":       file_path,
            "site_id":         resolved_site_id,
            "mime_type":       mime_type,
            "size_bytes":      size_bytes,
            "graph_url":       graph_url,
            "source":          "sharepoint",
        }

        log_info(
            "SharePoint file extracted successfully.",
            context={"file": file_name, "chars": len(text)},
        )
        return {"text": text, "metadata": metadata}

    # ── health_check ──────────────────────────────────────────────────────────

    async def health_check(self) -> bool:  # type: ignore[override]
        """
        Verify the Graph API is reachable using the current access token.

        Returns:
            True if healthy, False otherwise.
        """
        if not self._access_token:
            return False
        try:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{_GRAPH_BASE}/me", headers=headers)
                healthy = resp.status_code in (200, 400)  # 400 = app-only token (no /me)
            log_info(f"SharePoint health check result: {healthy}")
            return healthy
        except Exception as exc:
            log_warning(f"SharePoint health check failed: {exc}")
            return False


# ─── INTEGRATION NOTE ─────────────────────────────────────────────────────────
# Produces : {"text": str, "metadata": dict}  (from fetch())
# Consumed : ingestion/__init__.py  run_ingestion() for source_type == "sharepoint"
