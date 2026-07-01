import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_get_jira_projects():
    response = client.get("/connectors/jira/projects")
    assert response.status_code == 200
    data = response.json()
    assert "projects" in data
    assert len(data["projects"]) > 0
    assert data["projects"][0]["key"] == "HRMS"

def test_get_jira_epics():
    response = client.get("/connectors/jira/epics?project_id=PROJ-HRMS")
    assert response.status_code == 200
    data = response.json()
    assert "epics" in data
    assert len(data["epics"]) > 0

def test_get_jira_stories():
    response = client.get("/connectors/jira/stories?epic_id=EPIC-LEAVE")
    assert response.status_code == 200
    data = response.json()
    assert "stories" in data
    assert len(data["stories"]) > 0

def test_get_confluence_spaces():
    response = client.get("/connectors/confluence/spaces")
    assert response.status_code == 200
    data = response.json()
    assert "spaces" in data
    assert len(data["spaces"]) > 0

@pytest.mark.anyio
async def test_connector_import_jira():
    payload = {
        "source_type": "JIRA",
        "project_id": "PROJ-HRMS",
        "epic_id": "EPIC-LEAVE",
        "story_id": "STORY-APPLY"
    }
    # Mocking graph run and JiraConnector to prevent background tasks and network calls
    from unittest.mock import patch, AsyncMock, MagicMock
    with patch("backend.api.routes.connectors.pipeline_graph.ainvoke", new_callable=AsyncMock) as mock_graph, \
         patch("backend.ingestion.connectors.jira_connector.JiraConnector.authenticate", return_value=None), \
         patch("backend.ingestion.connectors.jira_connector.JiraConnector.fetch", new_callable=AsyncMock) as mock_fetch:
        
        mock_fetch.return_value = {"text": "mock jira text", "metadata": {}}
        response = client.post("/connectors/import", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert data["source_type"] == "JIRA"
        assert data["status"] == "RUNNING"

@pytest.mark.anyio
async def test_preview_ingest_jira():
    payload = {
        "source_type": "JIRA",
        "target_identifier": "STORY-APPLY"
    }
    from unittest.mock import patch, MagicMock, AsyncMock
    # Mock domain detection to run fast and avoid LLM calls
    mock_domain_res = MagicMock()
    mock_domain_res.primary_domain = "HRMS"
    mock_domain_res.secondary_domains = ["Banking"]
    mock_domain_res.confidence = 90
    mock_domain_res.reasoning = "Test reasoning"
    
    with patch("backend.api.routes.ingest.DomainDetectionModule.detect_domain", new_callable=AsyncMock) as mock_detect, \
         patch("backend.ingestion.connectors.jira_connector.JiraConnector.authenticate", return_value=None), \
         patch("backend.ingestion.connectors.jira_connector.JiraConnector.fetch", new_callable=AsyncMock) as mock_fetch:
        
        mock_fetch.return_value = {"text": "mock jira text", "metadata": {}}
        mock_detect.return_value = mock_domain_res
        response = client.post("/ingest/preview", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["source_type"] == "JIRA"
        assert data["domain"]["primary_domain"] == "HRMS"
        assert "requirement_package_preview" in data


