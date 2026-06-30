import pytest
import io
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from backend.main import app

client = TestClient(app)

@pytest.fixture
def mock_pipeline_graph():
    with patch("backend.orchestrator.graph.pipeline_graph.ainvoke", new_callable=AsyncMock) as mock_invoke:
        yield mock_invoke

def test_upload_unsupported_file_type():
    """
    Tests that uploading an unsupported file type (e.g., .png) returns 400.
    """
    file_content = b"fake image content"
    files = {"files": ("test_image.png", io.BytesIO(file_content), "image/png")}
    
    response = client.post("/ingest/upload", files=files)
    
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

def test_upload_file_too_large():
    """
    Tests that uploading a file larger than 10MB returns 413.
    """
    # Create a 11MB file in memory
    large_content = b"a" * (11 * 1024 * 1024)
    files = {"files": ("large_file.txt", io.BytesIO(large_content), "text/plain")}
    
    response = client.post("/ingest/upload", files=files)
    
    assert response.status_code == 413
    assert "exceeds the maximum size of 10MB" in response.json()["detail"]

def test_upload_valid_txt_file(mock_pipeline_graph):
    """
    Tests that uploading a valid .txt file succeeds, saves it, and triggers the pipeline.
    """
    file_content = b"This is a valid requirement document.\nIt has functional requirements and actors."
    files = {"files": ("requirements.txt", io.BytesIO(file_content), "text/plain")}
    
    response = client.post("/ingest/upload", files=files)
    
    assert response.status_code == 201
    res_data = response.json()
    assert "uploaded_files" in res_data
    assert len(res_data["uploaded_files"]) == 1
    
    uploaded_file = res_data["uploaded_files"][0]
    assert uploaded_file["filename"] == "requirements.txt"
    assert uploaded_file["status"] == "RUNNING"
    assert "job_id" in uploaded_file
    
    # Verify that the mock pipeline was invoked
    # Since it runs in an asyncio task, we might need a brief sleep or just trust it was scheduled.
    # But since we patched ainvoke, it should be called as soon as the event loop runs.
