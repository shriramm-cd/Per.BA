"""
=== FILE: backend/ingestion/connectors/base_connector.py ===

Abstract base class for all ingestion connectors.
Every concrete connector must implement authenticate(), fetch(),
health_check(), and fetch_and_normalize().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from designlab_core.utilities.logger import get_logger

logger = get_logger("ingestion.connectors.base")


class BaseConnector(ABC):
    """
    Abstract interface defining the contract for every ingestion connector.

    Subclasses:
        JiraConnector, ConfluenceConnector, SharePointConnector, GDriveConnector

    All fetch methods must return:
        {
            "text": str,
            "metadata": dict
        }
    """

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def authenticate(self) -> None:
        """
        Validate credentials and initialise the API client.
        Must raise shared.exceptions.ConnectorAuthError on failure.
        """
        ...

    @abstractmethod
    async def fetch(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Fetch raw content from the source system.

        Returns:
            {"text": str, "metadata": dict}
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify the connector is authenticated and the remote service is reachable.

        Returns:
            True if healthy, False otherwise.
        """
        ...

    # ── Concrete helper ────────────────────────────────────────────────────────

    async def fetch_and_normalize(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Convenience wrapper: fetch() then apply basic whitespace normalization.
        Connectors may override this for source-specific post-processing.

        Returns:
            {"text": str, "metadata": dict}
        """
        result = await self.fetch(*args, **kwargs)
        raw_text: str = result.get("text", "")

        # Light normalization (full pipeline runs in run_ingestion)
        import re
        text = re.sub(r"\r\n", "\n", raw_text)
        text = re.sub(r"\r", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        result["text"] = text
        return result


# ─── INTEGRATION NOTE ─────────────────────────────────────────────────────────
# Produces : BaseConnector ABC
# Consumed : JiraConnector, ConfluenceConnector, SharePointConnector, GDriveConnector
