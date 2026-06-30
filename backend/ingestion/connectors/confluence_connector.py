"""
=== FILE: backend/ingestion/connectors/confluence_connector.py ===

Confluence connector.

  - Authenticate via Atlassian Python API (Basic Auth / Cloud token)
  - Fetch page by ID (title + body storage HTML)
  - Strip HTML tags using regex (BeautifulSoup not required)
  - Recursively fetch child pages (optional)
  - Health-check via current_user()
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from atlassian import Confluence

from designlab_core.utilities.env import get_env
from designlab_core.utilities.logger import get_logger, log_error, log_info, log_warning

from backend.shared.exceptions import ConnectorAuthError
from .base_connector import BaseConnector

logger = get_logger("ingestion.connectors.confluence")

# ── HTML stripping helpers ─────────────────────────────────────────────────────

_HTML_TAG_RE   = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s{2,}")


def _strip_html(html: str) -> str:
    """Remove all HTML tags and collapse excess whitespace."""
    text = _HTML_TAG_RE.sub(" ", html)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


class ConfluenceConnector(BaseConnector):
    """
    Fetches page content from Atlassian Confluence.
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
            or env.model_extra.get("confluence_server_url")
            or env.model_extra.get("CONFLUENCE_SERVER_URL")
            or ""
        )
        self._username: str = (
            username
            or env.model_extra.get("confluence_username")
            or env.model_extra.get("CONFLUENCE_USERNAME")
            or ""
        )
        self._api_token: str = (
            api_token
            or env.model_extra.get("confluence_api_token")
            or env.model_extra.get("CONFLUENCE_API_TOKEN")
            or ""
        )
        self._client: Confluence | None = None

    # ── authenticate ──────────────────────────────────────────────────────────

    def authenticate(self) -> None:
        """
        Initialise the Confluence client and verify credentials.
        Raises ConnectorAuthError on failure.
        """
        if not self._server_url or not self._username or not self._api_token:
            raise ConnectorAuthError(
                "Confluence credentials incomplete. Set CONFLUENCE_SERVER_URL, "
                "CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN in your .env file."
            )
        try:
            client = Confluence(
                url=self._server_url,
                username=self._username,
                password=self._api_token,
                cloud=True,
            )
            # Validate: fetch current user
            user = client.get_current_user()
            log_info(
                "Confluence authentication successful.",
                context={
                    "user": user.get("displayName", "") if isinstance(user, dict) else "",
                    "url": self._server_url,
                },
            )
            self._client = client
        except ConnectorAuthError:
            raise
        except Exception as exc:
            raise ConnectorAuthError(
                f"Confluence authentication failed for '{self._server_url}': {exc}"
            ) from exc

    # ── fetch ─────────────────────────────────────────────────────────────────

    async def fetch(  # type: ignore[override]
        self,
        page_id: str,
        include_children: bool = False,
    ) -> dict[str, Any]:
        """
        Fetch a Confluence page and optionally its children.

        Args:
            page_id:          Confluence page ID (numeric string).
            include_children: If True, also fetch and append child page content.

        Returns:
            {"text": str, "metadata": dict}
        """
        if self._client is None:
            raise ConnectorAuthError(
                "Confluence client not initialised. Call authenticate() first."
            )

        log_info("Fetching Confluence page.", context={"page_id": page_id})

        def _fetch_page_sync() -> dict[str, Any]:
            try:
                return self._client.get_page_by_id(  # type: ignore[union-attr]
                    page_id=page_id,
                    expand="body.storage,ancestors,version",
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Confluence API error for page '{page_id}': {exc}"
                ) from exc

        page = await asyncio.to_thread(_fetch_page_sync)
        title    = page.get("title", "Untitled")
        body_html = page.get("body", {}).get("storage", {}).get("value", "")
        body_text = _strip_html(body_html)

        # Ancestors breadcrumb
        ancestors = page.get("ancestors", [])
        breadcrumb = " > ".join(a.get("title", "") for a in ancestors) + f" > {title}"

        version = page.get("version", {}).get("number", "")
        space   = page.get("space", {}).get("key", "")

        text_parts: list[str] = [
            f"Confluence Page: {title}",
            f"Breadcrumb: {breadcrumb}",
            f"Version: {version}",
            f"Space: {space}",
            "",
            body_text,
        ]

        # ── Optional: child pages ─────────────────────────────────────────────
        child_pages_fetched: list[str] = []
        if include_children:
            def _get_children() -> list[dict[str, Any]]:
                return self._client.get_child_pages(page_id=page_id)  # type: ignore[union-attr]

            children = await asyncio.to_thread(_get_children)
            for child in children[:10]:  # guard against very large spaces
                child_id    = child.get("id", "")
                child_title = child.get("title", "")
                try:
                    child_result = await self.fetch(child_id, include_children=False)
                    text_parts += [
                        "",
                        f"--- Child Page: {child_title} ---",
                        child_result["text"],
                    ]
                    child_pages_fetched.append(child_title)
                except Exception as exc:
                    log_warning(f"Failed to fetch child page '{child_title}': {exc}")

        combined = "\n".join(text_parts)
        metadata: dict[str, Any] = {
            "page_id":             page_id,
            "title":               title,
            "breadcrumb":          breadcrumb,
            "version":             version,
            "space":               space,
            "child_pages_fetched": child_pages_fetched,
            "source":              "confluence",
        }

        return {"text": combined, "metadata": metadata}

    # ── health_check ──────────────────────────────────────────────────────────

    async def health_check(self) -> bool:  # type: ignore[override]
        """
        Ping Confluence by requesting the current user.

        Returns:
            True if healthy, False otherwise.
        """
        if self._client is None:
            return False
        try:
            def _check():
                return self._client.get_current_user()  # type: ignore[union-attr]
            await asyncio.to_thread(_check)
            log_info("Confluence health check passed.")
            return True
        except Exception as exc:
            log_warning(f"Confluence health check failed: {exc}")
            return False


# ─── INTEGRATION NOTE ─────────────────────────────────────────────────────────
# Produces : {"text": str, "metadata": dict}  (from fetch())
# Consumed : ingestion/__init__.py  run_ingestion() for source_type == "confluence"
