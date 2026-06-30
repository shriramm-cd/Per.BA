"""
=== FILE: backend/ingestion/tests/test_docling_loader.py ===
Tests for docling_loader.py
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── load_from_file ─────────────────────────────────────────────────────────────

class TestLoadFromFile:
    @pytest.mark.asyncio
    async def test_load_txt_fast_path(self, tmp_path):
        """Plain .txt files are read directly without Docling."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello world requirements.", encoding="utf-8")

        from backend.ingestion.docling_loader import load_from_file
        result = await load_from_file(str(txt_file))

        assert "text" in result
        assert "Hello world" in result["text"]
        assert result["metadata"].get("source") == "txt_read"

    @pytest.mark.asyncio
    async def test_load_file_not_found(self):
        """Raises FileNotFoundError for a missing path."""
        from backend.ingestion.docling_loader import load_from_file

        with pytest.raises(FileNotFoundError):
            await load_from_file("/nonexistent/path/to/file.pdf")

    @pytest.mark.asyncio
    async def test_load_pdf_via_docling(self, tmp_path):
        """A .pdf file is sent through Docling and returns text + metadata."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 mock pdf content")

        mock_doc = MagicMock()
        mock_doc.export_to_markdown.return_value = "# Requirements\nSome content."
        mock_doc.pages = [MagicMock()]
        mock_doc.title = "Test Document"
        mock_result = MagicMock()
        mock_result.document = mock_doc

        mock_converter = MagicMock()
        mock_converter.convert.return_value = mock_result

        with patch("backend.ingestion.docling_loader._get_converter", return_value=mock_converter):
            from backend.ingestion.docling_loader import load_from_file
            result = await load_from_file(str(pdf_file))

        assert "text" in result
        assert "Requirements" in result["text"]
        assert result["metadata"]["extraction_method"] == "docling"

    @pytest.mark.asyncio
    async def test_load_file_docling_failure_fallback(self, tmp_path):
        """On Docling failure, falls back to reading file as text."""
        doc_file = tmp_path / "fallback.docx"
        doc_file.write_text("Fallback text content.", encoding="utf-8")

        with patch("backend.ingestion.docling_loader._get_converter", side_effect=RuntimeError("Docling boom")):
            from backend.ingestion.docling_loader import load_from_file
            result = await load_from_file(str(doc_file))

        assert "Fallback text content." in result["text"]
        assert result["metadata"].get("extraction_method") == "text_fallback"


# ── load_from_url ──────────────────────────────────────────────────────────────

class TestLoadFromUrl:
    @pytest.mark.asyncio
    async def test_load_url_success(self, tmp_path):
        """Downloads content and delegates to load_from_file."""
        import httpx

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"PDF content"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.raise_for_status = MagicMock()

        mock_load = AsyncMock(return_value={
            "text": "Extracted PDF text",
            "metadata": {"extraction_method": "docling"},
        })

        with patch("httpx.AsyncClient") as mock_client_cls, \
             patch("backend.ingestion.docling_loader.load_from_file", mock_load):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            from backend.ingestion.docling_loader import load_from_url
            result = await load_from_url("https://example.com/doc.pdf")

        assert result["text"] == "Extracted PDF text"
        assert result["metadata"]["source_url"] == "https://example.com/doc.pdf"

    @pytest.mark.asyncio
    async def test_load_url_http_error(self):
        """Raises RuntimeError on HTTP error status."""
        import httpx

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            from backend.ingestion.docling_loader import load_from_url
            with pytest.raises(RuntimeError, match="HTTP error"):
                await load_from_url("https://example.com/missing.pdf")
