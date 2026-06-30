"""
=== FILE: backend/ingestion/connectors/jira_connector.py ===

Jira connector — PRIMARY ingestion source.

Capabilities
  - Authenticate via Atlassian Python API (Basic Auth / Cloud token)
  - Fetch all standard issue fields (summary, description, acceptance criteria,
    issue type, priority, status, labels, reporter, assignee)
  - Download attachments (selected or all), extract text via Docling
  - Fetch all issues in a project (with pagination)
  - Health-check via `myself()`
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from typing import Any

import requests
from atlassian import Jira

from designlab_core.utilities.env import get_env
from designlab_core.utilities.logger import get_logger, log_error, log_info, log_warning

from backend.shared.exceptions import ConnectorAuthError
from .base_connector import BaseConnector

logger = get_logger("ingestion.connectors.jira")

# ── Acceptance Criteria custom-field heuristics ───────────────────────────────
_AC_FIELD_PATTERNS = re.compile(
    r"(acceptance.criteria|customfield_\d+)",
    re.IGNORECASE,
)


def _extract_acceptance_criteria(fields: dict[str, Any]) -> str:
    """
    Try to extract acceptance criteria from known or discovered custom fields.
    Falls back to empty string if not found.
    """
    # 1. Try the well-known key "customfield_10016" (Jira Cloud AC field)
    for key, value in fields.items():
        if _AC_FIELD_PATTERNS.search(key) and value:
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                return value.get("value", "") or value.get("description", "")
    return ""


def _safe_name(obj: Any) -> str:
    """Extract display name from a Jira user/object dict."""
    if obj is None:
        return ""
    if isinstance(obj, dict):
        return obj.get("displayName") or obj.get("name") or ""
    return str(obj)


def _safe_str(obj: Any) -> str:
    if obj is None:
        return ""
    return str(obj)


class JiraConnector(BaseConnector):
    """
    Fetches requirements content from Jira issues including attachments.
    """

    def __init__(
        self,
        server_url: str | None = None,
        username: str | None = None,
        api_token: str | None = None,
    ) -> None:
        env = get_env()
        self._server_url: str = (
            server_url
            or env.model_extra.get("jira_server_url")
            or env.model_extra.get("JIRA_SERVER_URL")
            or ""
        )
        self._username: str = (
            username
            or env.model_extra.get("jira_username")
            or env.model_extra.get("JIRA_USERNAME")
            or ""
        )
        self._api_token: str = (
            api_token
            or env.model_extra.get("jira_api_token")
            or env.model_extra.get("JIRA_API_TOKEN")
            or ""
        )
        self._client: Jira | None = None

    # ── authenticate ──────────────────────────────────────────────────────────

    def authenticate(self) -> None:
        """
        Initialise the Jira client and verify credentials via myself().
        Raises ConnectorAuthError on any failure.
        """
        if not self._server_url or not self._username or not self._api_token:
            raise ConnectorAuthError(
                "Jira credentials incomplete. Set JIRA_SERVER_URL, JIRA_USERNAME, "
                "JIRA_API_TOKEN in your .env file."
            )
        try:
            client = Jira(
                url=self._server_url,
                username=self._username,
                password=self._api_token,
                cloud=True,
            )
            # Validate credentials — raises if auth fails
            myself = client.myself()
            log_info(
                "Jira authentication successful.",
                context={"user": myself.get("displayName", ""), "url": self._server_url},
            )
            self._client = client
        except ConnectorAuthError:
            raise
        except Exception as exc:
            raise ConnectorAuthError(
                f"Jira authentication failed for '{self._server_url}': {exc}"
            ) from exc

    # ── fetch ─────────────────────────────────────────────────────────────────

    async def fetch(  # type: ignore[override]
        self,
        issue_key: str,
        attachment_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch all content for a Jira issue.

        Step 1 — Issue fields (summary, description, AC, type, priority, etc.)
        Step 2 — Attachments: download selected or all, extract text via Docling
        Step 3 — Return combined text + metadata dict

        Args:
            issue_key:       Jira issue key, e.g. "PROJ-123".
            attachment_name: If set, only download this attachment by name.

        Returns:
            {"text": str, "metadata": dict}

        Raises:
            ConnectorAuthError: If authenticate() was not called first.
            RuntimeError:       If the Jira API call fails.
        """
        if self._client is None:
            raise ConnectorAuthError(
                "Jira client not initialised. Call authenticate() first."
            )

        log_info("Fetching Jira issue.", context={"issue": issue_key})

        # ── Step 1: Issue fields ──────────────────────────────────────────────
        def _fetch_issue_sync() -> dict[str, Any]:
            try:
                return self._client.issue(issue_key)  # type: ignore[union-attr]
            except Exception as exc:
                raise RuntimeError(
                    f"Jira API error fetching '{issue_key}': {exc}"
                ) from exc

        issue_data = await asyncio.to_thread(_fetch_issue_sync)
        fields: dict[str, Any] = issue_data.get("fields", {})

        summary     = _safe_str(fields.get("summary"))
        description = _safe_str(fields.get("description"))
        ac          = _extract_acceptance_criteria(fields)
        issue_type  = _safe_str((fields.get("issuetype") or {}).get("name"))
        priority    = _safe_str((fields.get("priority") or {}).get("name"))
        status      = _safe_str((fields.get("status") or {}).get("name"))
        labels      = fields.get("labels", [])
        reporter    = _safe_name(fields.get("reporter"))
        assignee    = _safe_name(fields.get("assignee"))

        text_parts: list[str] = [
            f"Jira Issue: {issue_key}",
            f"Summary: {summary}",
            f"Issue Type: {issue_type}",
            f"Priority: {priority}",
            f"Status: {status}",
            f"Reporter: {reporter}",
            f"Assignee: {assignee}",
            f"Labels: {', '.join(labels) if labels else 'None'}",
            "",
            "Description:",
            description,
        ]
        if ac:
            text_parts += ["", "Acceptance Criteria:", ac]

        # ── Step 2: Attachments ───────────────────────────────────────────────
        attachments: list[dict[str, Any]] = fields.get("attachment", []) or []
        attachments_processed: list[str] = []

        # Filter by name if requested
        if attachment_name:
            attachments = [
                a for a in attachments
                if a.get("filename", "") == attachment_name
            ]
            if not attachments:
                log_warning(
                    f"Attachment '{attachment_name}' not found in issue '{issue_key}'."
                )

        for attachment in attachments:
            att_name = attachment.get("filename", "unknown")
            att_url  = attachment.get("content", "")
            if not att_url:
                continue

            att_text = await self._download_and_extract(att_url, att_name)
            if att_text:
                text_parts += [
                    "",
                    f"--- Attachment: {att_name} ---",
                    att_text,
                ]
                attachments_processed.append(att_name)
                log_info(
                    "Attachment extracted.",
                    context={"attachment": att_name, "issue": issue_key},
                )

        # ── Step 3: Build result ──────────────────────────────────────────────
        combined_text = "\n".join(text_parts)
        metadata: dict[str, Any] = {
            "issue_key":              issue_key,
            "summary":                summary,
            "status":                 status,
            "priority":               priority,
            "labels":                 labels,
            "issue_type":             issue_type,
            "reporter":               reporter,
            "assignee":               assignee,
            "attachments_processed":  attachments_processed,
            "source":                 "jira",
        }

        return {"text": combined_text, "metadata": metadata}

    # ── health_check ──────────────────────────────────────────────────────────

    async def health_check(self) -> bool:  # type: ignore[override]
        """
        Verify the Jira connection is alive by calling myself().

        Returns:
            True if healthy, False otherwise.
        """
        if self._client is None:
            return False
        try:
            def _check():
                return self._client.myself()  # type: ignore[union-attr]
            await asyncio.to_thread(_check)
            log_info("Jira health check passed.")
            return True
        except Exception as exc:
            log_warning(f"Jira health check failed: {exc}")
            return False

    # ── get_all_issues_in_project ─────────────────────────────────────────────

    async def get_all_issues_in_project(
        self,
        project_key: str,
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Return a list of all issue dicts in the given project (paginated).

        Args:
            project_key: Jira project key, e.g. "PROJ".
            max_results: Page size per API request.

        Returns:
            List of raw Jira issue dicts.
        """
        if self._client is None:
            raise ConnectorAuthError("Jira client not initialised.")

        all_issues: list[dict[str, Any]] = []
        start_at = 0

        while True:
            def _page(start: int = start_at) -> list[dict[str, Any]]:
                return self._client.jql(  # type: ignore[union-attr]
                    f"project = {project_key} ORDER BY created DESC",
                    start=start,
                    limit=max_results,
                ).get("issues", [])

            page = await asyncio.to_thread(_page)
            if not page:
                break
            all_issues.extend(page)
            if len(page) < max_results:
                break
            start_at += max_results

        log_info(
            "Fetched all issues in project.",
            context={"project": project_key, "total": len(all_issues)},
        )
        return all_issues

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _download_and_extract(self, url: str, filename: str) -> str:
        """
        Download an attachment using Basic Auth and extract text via Docling.
        Saves to a temp file, extracts, then deletes.

        Returns:
            Extracted text, or empty string on failure.
        """
        try:
            auth = (self._username, self._api_token)

            def _download() -> bytes:
                response = requests.get(url, auth=auth, timeout=60)
                response.raise_for_status()
                return response.content

            content = await asyncio.to_thread(_download)

            # Determine file extension
            suffix = os.path.splitext(filename)[1] or ".bin"

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, prefix="jira_att_"
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                from ..docling_loader import load_from_file
                result = await load_from_file(tmp_path)
                return result.get("text", "")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as exc:
            log_error(
                "Failed to download/extract Jira attachment.",
                exc=exc,
                context={"url": url, "filename": filename},
            )
            return ""


# ─── INTEGRATION NOTE ─────────────────────────────────────────────────────────
# Produces : {"text": str, "metadata": dict}  (from fetch())
# Consumed : ingestion/__init__.py  run_ingestion() for source_type == "jira"
