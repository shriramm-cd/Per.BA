"""
=== FILE: backend/ingestion/tests/test_connectors.py ===

Connector test suite.

Jira  (7 required cases)
  ✔ authenticate success
  ✔ authenticate failure
  ✔ fetch without attachment
  ✔ fetch with attachment
  ✔ invalid issue key
  ✔ health_check returns True
  ✔ health_check returns False

Confluence (3 basic cases)
SharePoint (3 basic cases)
GDrive     (3 basic cases)
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


# ══════════════════════════════════════════════════════════════════════════════
# JIRA CONNECTOR
# ══════════════════════════════════════════════════════════════════════════════

class TestJiraConnectorAuthenticate:
    """Test authenticate() — success and failure paths."""

    def _make_connector(self, server_url="https://jira.test", username="user", token="tok"):
        from backend.ingestion.connectors.jira_connector import JiraConnector
        return JiraConnector(server_url=server_url, username=username, api_token=token)

    def test_authenticate_success(self):
        """authenticate() initialises client and calls myself()."""
        connector = self._make_connector()

        mock_client = MagicMock()
        mock_client.myself.return_value = {"displayName": "Test User"}

        with patch("backend.ingestion.connectors.jira_connector.Jira", return_value=mock_client):
            connector.authenticate()

        assert connector._client is mock_client
        mock_client.myself.assert_called_once()

    def test_authenticate_failure_missing_credentials(self):
        """Missing credentials raise ConnectorAuthError immediately."""
        from backend.shared.exceptions import ConnectorAuthError
        from backend.ingestion.connectors.jira_connector import JiraConnector

        connector = JiraConnector(server_url="", username="", api_token="")

        with pytest.raises(ConnectorAuthError, match="Jira credentials incomplete"):
            connector.authenticate()

    def test_authenticate_failure_api_error(self):
        """API call failure raises ConnectorAuthError."""
        from backend.shared.exceptions import ConnectorAuthError
        connector = self._make_connector()

        mock_client = MagicMock()
        mock_client.myself.side_effect = Exception("401 Unauthorized")

        with patch("backend.ingestion.connectors.jira_connector.Jira", return_value=mock_client), \
             pytest.raises(ConnectorAuthError, match="Jira authentication failed"):
            connector.authenticate()


class TestJiraConnectorFetch:
    """Test fetch() — with and without attachments."""

    def _make_authenticated_connector(self):
        from backend.ingestion.connectors.jira_connector import JiraConnector
        connector = JiraConnector(
            server_url="https://jira.test",
            username="user",
            api_token="token",
        )
        mock_client = MagicMock()
        mock_client.myself.return_value = {"displayName": "Test User"}

        with patch("backend.ingestion.connectors.jira_connector.Jira", return_value=mock_client):
            connector.authenticate()

        return connector, mock_client

    @pytest.mark.asyncio
    async def test_fetch_without_attachment(self):
        """Fetch returns combined text with no attachment sections."""
        connector, mock_client = self._make_authenticated_connector()

        mock_client.issue.return_value = {
            "fields": {
                "summary": "Login feature",
                "description": "As a user I can log in.",
                "issuetype": {"name": "Story"},
                "priority": {"name": "High"},
                "status": {"name": "Open"},
                "labels": ["auth", "login"],
                "reporter": {"displayName": "Alice"},
                "assignee": {"displayName": "Bob"},
                "attachment": [],
            }
        }

        result = await connector.fetch("PROJ-1")
        assert "Login feature" in result["text"]
        assert "As a user" in result["text"]
        assert result["metadata"]["issue_key"] == "PROJ-1"
        assert result["metadata"]["source"] == "jira"
        assert result["metadata"]["attachments_processed"] == []

    @pytest.mark.asyncio
    async def test_fetch_with_attachment(self):
        """Fetch downloads and extracts attachment text via Docling."""
        connector, mock_client = self._make_authenticated_connector()

        mock_client.issue.return_value = {
            "fields": {
                "summary": "BRD Review",
                "description": "Business requirements document.",
                "issuetype": {"name": "Task"},
                "priority": {"name": "Medium"},
                "status": {"name": "In Progress"},
                "labels": [],
                "reporter": {"displayName": "Alice"},
                "assignee": None,
                "attachment": [
                    {
                        "filename": "requirements.pdf",
                        "content": "https://jira.test/secure/attachment/1/requirements.pdf",
                    }
                ],
            }
        }

        mock_download_extract = AsyncMock(return_value="Extracted PDF text from requirements.")

        with patch.object(connector, "_download_and_extract", mock_download_extract):
            result = await connector.fetch("PROJ-2")

        assert "requirements.pdf" in result["text"]
        assert "Extracted PDF text" in result["text"]
        assert "requirements.pdf" in result["metadata"]["attachments_processed"]

    @pytest.mark.asyncio
    async def test_fetch_with_specific_attachment_name(self):
        """Only the named attachment is downloaded when attachment_name is set."""
        connector, mock_client = self._make_authenticated_connector()

        mock_client.issue.return_value = {
            "fields": {
                "summary": "Multi-attach issue",
                "description": "Has two attachments.",
                "issuetype": {"name": "Bug"},
                "priority": {"name": "Low"},
                "status": {"name": "Open"},
                "labels": [],
                "reporter": None,
                "assignee": None,
                "attachment": [
                    {"filename": "spec.docx", "content": "https://jira.test/att/1/spec.docx"},
                    {"filename": "notes.txt", "content": "https://jira.test/att/2/notes.txt"},
                ],
            }
        }

        download_calls: list[str] = []

        async def mock_download(url: str, filename: str) -> str:
            download_calls.append(filename)
            return f"Text from {filename}"

        with patch.object(connector, "_download_and_extract", side_effect=mock_download):
            result = await connector.fetch("PROJ-3", attachment_name="spec.docx")

        assert download_calls == ["spec.docx"]
        assert "notes.txt" not in result["text"]

    @pytest.mark.asyncio
    async def test_fetch_invalid_key(self):
        """RuntimeError is raised for a bad issue key."""
        connector, mock_client = self._make_authenticated_connector()
        mock_client.issue.side_effect = Exception("Issue does not exist")

        with pytest.raises(RuntimeError, match="Jira API error"):
            await connector.fetch("INVALID-9999")

    @pytest.mark.asyncio
    async def test_fetch_requires_authentication(self):
        """Fetching without authenticate() raises ConnectorAuthError."""
        from backend.shared.exceptions import ConnectorAuthError
        from backend.ingestion.connectors.jira_connector import JiraConnector

        connector = JiraConnector(
            server_url="https://jira.test", username="u", api_token="t"
        )
        with pytest.raises(ConnectorAuthError, match="not initialised"):
            await connector.fetch("PROJ-1")


class TestJiraConnectorHealthCheck:
    def _make_authenticated_connector(self):
        from backend.ingestion.connectors.jira_connector import JiraConnector
        connector = JiraConnector(
            server_url="https://jira.test", username="user", api_token="token"
        )
        mock_client = MagicMock()
        mock_client.myself.return_value = {"displayName": "User"}
        with patch("backend.ingestion.connectors.jira_connector.Jira", return_value=mock_client):
            connector.authenticate()
        return connector, mock_client

    @pytest.mark.asyncio
    async def test_health_check_true(self):
        """health_check returns True when myself() succeeds."""
        connector, mock_client = self._make_authenticated_connector()
        mock_client.myself.return_value = {"displayName": "User"}

        result = await connector.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_false(self):
        """health_check returns False when myself() raises."""
        connector, mock_client = self._make_authenticated_connector()
        mock_client.myself.side_effect = Exception("Connection refused")

        result = await connector.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_false_no_client(self):
        """health_check returns False when client is not initialised."""
        from backend.ingestion.connectors.jira_connector import JiraConnector
        connector = JiraConnector(server_url="x", username="u", api_token="t")

        result = await connector.health_check()
        assert result is False


# ══════════════════════════════════════════════════════════════════════════════
# CONFLUENCE CONNECTOR
# ══════════════════════════════════════════════════════════════════════════════

class TestConfluenceConnector:
    def _make_connector(self):
        from backend.ingestion.connectors.confluence_connector import ConfluenceConnector
        return ConfluenceConnector(
            server_url="https://wiki.test",
            username="user",
            api_token="token",
        )

    def test_authenticate_success(self):
        """authenticate() succeeds and sets _client."""
        connector = self._make_connector()

        mock_client = MagicMock()
        mock_client.get_current_user.return_value = {"displayName": "Wiki User"}

        with patch("backend.ingestion.connectors.confluence_connector.Confluence", return_value=mock_client):
            connector.authenticate()

        assert connector._client is mock_client

    def test_authenticate_failure(self):
        """Incorrect credentials raise ConnectorAuthError."""
        from backend.shared.exceptions import ConnectorAuthError
        from backend.ingestion.connectors.confluence_connector import ConfluenceConnector

        connector = ConfluenceConnector(server_url="", username="", api_token="")

        with pytest.raises(ConnectorAuthError, match="Confluence credentials incomplete"):
            connector.authenticate()

    @pytest.mark.asyncio
    async def test_fetch_page_success(self):
        """fetch() returns cleaned text and metadata for a valid page."""
        connector = self._make_connector()

        mock_client = MagicMock()
        mock_client.get_current_user.return_value = {"displayName": "User"}
        mock_client.get_page_by_id.return_value = {
            "title": "BA Requirements",
            "body": {
                "storage": {
                    "value": "<p>The user <strong>shall</strong> be able to log in.</p>"
                }
            },
            "ancestors": [{"title": "Project Docs"}],
            "version": {"number": 5},
            "space": {"key": "BA"},
        }

        with patch("backend.ingestion.connectors.confluence_connector.Confluence", return_value=mock_client):
            connector.authenticate()

        result = await connector.fetch("123456")

        assert "BA Requirements" in result["text"]
        assert "The user" in result["text"]
        assert "<p>" not in result["text"]
        assert result["metadata"]["page_id"] == "123456"
        assert result["metadata"]["source"] == "confluence"

    @pytest.mark.asyncio
    async def test_health_check_true(self):
        connector = self._make_connector()
        mock_client = MagicMock()
        mock_client.get_current_user.return_value = {"displayName": "User"}

        with patch("backend.ingestion.connectors.confluence_connector.Confluence", return_value=mock_client):
            connector.authenticate()

        result = await connector.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_false_no_client(self):
        connector = self._make_connector()
        result = await connector.health_check()
        assert result is False


# ══════════════════════════════════════════════════════════════════════════════
# SHAREPOINT CONNECTOR
# ══════════════════════════════════════════════════════════════════════════════

class TestSharePointConnector:
    def _make_connector(self):
        from backend.ingestion.connectors.sharepoint_connector import SharePointConnector
        return SharePointConnector(
            tenant_id="tenant-123",
            client_id="client-abc",
            client_secret="secret-xyz",
            site_id="site-001",
        )

    def test_authenticate_success(self):
        """authenticate() acquires a token and stores it."""
        connector = self._make_connector()

        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "my-access-token"
        }

        with patch("backend.ingestion.connectors.sharepoint_connector.msal.ConfidentialClientApplication",
                   return_value=mock_app):
            connector.authenticate()

        assert connector._access_token == "my-access-token"

    def test_authenticate_failure_msal_error(self):
        """MSAL token failure raises ConnectorAuthError."""
        from backend.shared.exceptions import ConnectorAuthError
        connector = self._make_connector()

        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Client secret wrong.",
        }

        with patch("backend.ingestion.connectors.sharepoint_connector.msal.ConfidentialClientApplication",
                   return_value=mock_app), \
             pytest.raises(ConnectorAuthError, match="MSAL token acquisition failed"):
            connector.authenticate()

    def test_authenticate_failure_missing_credentials(self):
        """Missing credentials raise ConnectorAuthError."""
        from backend.shared.exceptions import ConnectorAuthError
        from backend.ingestion.connectors.sharepoint_connector import SharePointConnector

        connector = SharePointConnector(tenant_id="", client_id="", client_secret="")

        with pytest.raises(ConnectorAuthError, match="SharePoint credentials incomplete"):
            connector.authenticate()

    @pytest.mark.asyncio
    async def test_fetch_success(self):
        """fetch() downloads file and returns extracted text + metadata."""
        connector = self._make_connector()
        connector._access_token = "token123"

        import httpx

        mock_meta_resp = MagicMock(spec=httpx.Response)
        mock_meta_resp.status_code = 200
        mock_meta_resp.json.return_value = {
            "name": "requirements.docx",
            "file": {"mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
            "size": 1024,
            "@microsoft.graph.downloadUrl": "https://download.example.com/file",
        }

        mock_content_resp = MagicMock(spec=httpx.Response)
        mock_content_resp.status_code = 200
        mock_content_resp.content = b"DOCX binary content"

        mock_load = AsyncMock(return_value={
            "text": "Extracted SharePoint requirements text.",
            "metadata": {},
        })

        async def mock_get(url, headers=None):
            if "content" in url or "download" in url:
                return mock_content_resp
            return mock_meta_resp

        with patch("backend.ingestion.connectors.sharepoint_connector.httpx.AsyncClient") as mock_cls, \
             patch("backend.ingestion.docling_loader.load_from_file", mock_load):
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.get = AsyncMock(side_effect=mock_get)
            mock_cls.return_value = mock_http

            result = await connector.fetch("drives/d1/items/i1")

        assert result["text"] == "Extracted SharePoint requirements text."
        assert result["metadata"]["source"] == "sharepoint"

    @pytest.mark.asyncio
    async def test_health_check_false_no_token(self):
        """health_check returns False with no access token."""
        connector = self._make_connector()
        result = await connector.health_check()
        assert result is False


# ══════════════════════════════════════════════════════════════════════════════
# GDRIVE CONNECTOR
# ══════════════════════════════════════════════════════════════════════════════

class TestGDriveConnector:
    def _make_connector(self, creds_json: str = '{"type":"service_account"}'):
        from backend.ingestion.connectors.gdrive_connector import GDriveConnector
        return GDriveConnector(credentials_json=creds_json)

    def test_authenticate_success_inline_json(self):
        """authenticate() with inline JSON string builds Drive service."""
        connector = self._make_connector(creds_json='{"type":"service_account","project_id":"p"}')

        mock_creds = MagicMock()
        mock_service = MagicMock()

        with patch("google.oauth2.service_account.Credentials.from_service_account_info",
                   return_value=mock_creds) as mock_from_info, \
             patch("googleapiclient.discovery.build", return_value=mock_service):
            connector.authenticate()

        assert connector._service is mock_service

    def test_authenticate_failure_no_credentials(self):
        """Missing credentials raise ConnectorAuthError."""
        from backend.shared.exceptions import ConnectorAuthError
        from backend.ingestion.connectors.gdrive_connector import GDriveConnector

        connector = GDriveConnector(credentials_json="")
        with pytest.raises(ConnectorAuthError, match="Google Drive credentials not set"):
            connector.authenticate()

    @pytest.mark.asyncio
    async def test_fetch_google_doc_export(self):
        """Google Docs files are exported as plain text."""
        connector = self._make_connector()
        connector._service = MagicMock()

        # Simulate files().get().execute()
        mock_file_meta = {
            "id": "file123",
            "name": "BRD.gdoc",
            "mimeType": "application/vnd.google-apps.document",
            "size": None,
            "createdTime": "2024-01-01T00:00:00Z",
            "modifiedTime": "2024-01-02T00:00:00Z",
        }

        mock_files = MagicMock()
        mock_files.get.return_value.execute.return_value = mock_file_meta
        connector._service.files.return_value = mock_files

        # Simulate MediaIoBaseDownload writing bytes
        export_text = b"Business requirements document content."

        def mock_download_sync():
            from io import BytesIO
            buf = BytesIO(export_text)

            class FakeDownloader:
                def next_chunk(self):
                    return MagicMock(progress=lambda: 1.0), True

            return export_text, mock_file_meta



        # Patch asyncio.to_thread to call mock_download_sync directly
        import asyncio

        async def mock_to_thread(fn, *args, **kwargs):
            return mock_download_sync()

        with patch("backend.ingestion.connectors.gdrive_connector.asyncio.to_thread", new=mock_to_thread):
            result = await connector.fetch("file123")

        assert "Business requirements" in result["text"]
        assert result["metadata"]["source"] == "gdrive"
        assert result["metadata"]["file_id"] == "file123"

    @pytest.mark.asyncio
    async def test_health_check_false_no_service(self):
        """health_check returns False when service is not initialised."""
        connector = self._make_connector()
        result = await connector.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_true(self):
        """health_check returns True when files().list() succeeds."""
        connector = self._make_connector()
        connector._service = MagicMock()
        connector._service.files.return_value.list.return_value.execute.return_value = {"files": []}

        result = await connector.health_check()
        assert result is True


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION: run_ingestion
# ══════════════════════════════════════════════════════════════════════════════

class TestRunIngestion:
    """End-to-end test of the run_ingestion() entrypoint."""

    @pytest.mark.asyncio
    async def test_run_ingestion_txt_file(self, tmp_path):
        """Full pipeline from txt file to IngestionOutput."""
        txt = tmp_path / "req.txt"
        txt.write_text(
            "The user shall be able to log in using email and password. " * 30,
            encoding="utf-8",
        )

        from backend.ingestion.schemas import IngestionInput, IngestionOutput, SourceType
        from backend.ingestion import run_ingestion

        inp = IngestionInput(
            source_type=SourceType.txt,
            file_path=str(txt),
        )

        output = await run_ingestion(inp, redis_client=None)

        assert isinstance(output, IngestionOutput)
        assert len(output.text) > 0
        assert len(output.fingerprint) == 64
        assert output.chunk_count >= 1
        assert len(output.chunks) == output.chunk_count
        assert output.char_count == len(output.text)
        assert output.source_type == "txt"
        assert output.language != ""
        assert output.extraction_method != ""
        assert output.confidence_score == 1.0
        assert output.is_duplicate is False

    @pytest.mark.asyncio
    async def test_run_ingestion_deduplication(self, tmp_path):
        """Second ingestion of same document returns is_duplicate=True."""
        txt = tmp_path / "dup.txt"
        txt.write_text("Duplicate requirement content. " * 50, encoding="utf-8")

        from backend.ingestion.schemas import IngestionInput, SourceType
        from backend.ingestion import run_ingestion

        inp = IngestionInput(source_type=SourceType.txt, file_path=str(txt))

        mock_redis = AsyncMock()
        # First call: key does not exist → False; register it
        # Second call: key exists → True
        call_count = {"n": 0}

        async def mock_exists(key):
            call_count["n"] += 1
            return 1 if call_count["n"] > 1 else 0

        mock_redis.exists = AsyncMock(side_effect=mock_exists)
        mock_redis.set = AsyncMock(return_value=True)

        out1 = await run_ingestion(inp, redis_client=mock_redis)
        out2 = await run_ingestion(inp, redis_client=mock_redis)

        assert out1.is_duplicate is False
        assert out2.is_duplicate is True
